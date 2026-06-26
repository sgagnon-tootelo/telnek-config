import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import {
  markAppointmentCancelledInGoogleCalendar,
  markAppointmentConfirmedInGoogleCalendar,
} from './google_calendar.ts'

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

const twilioSid = Deno.env.get('TWILIO_ACCOUNT_SID')
const twilioToken = Deno.env.get('TWILIO_AUTH_TOKEN')
const fromNumber = Deno.env.get('TWILIO_FROM_NUMBER')

const DEBUG_MODE = false

type AppointmentRow = {
  id: string
  client_id: string | null
  google_event_id: string | null
  appointment_name: string | null
  appointment_number: string | null
  caller_number: string | null
  appointment_confirmed: boolean | null
  appointment_cancelled: boolean | null
  reminder_sent: boolean | null
  started_at: string | null
  appointment_start: string | null
}

type ClientCalendarConfig = {
  google_refresh_token: string | null
  calendar_id: string | null
}

function normalizePhone(raw: string): string {
  let clean = raw.replace(/\D/g, '')
  if (clean.startsWith('1') && clean.length === 11) clean = clean.substring(1)
  return clean
}

function isPendingConfirmation(rdv: AppointmentRow): boolean {
  return rdv.appointment_confirmed !== true && rdv.appointment_cancelled !== true
}

function pickPendingAppointment(rows: AppointmentRow[]): AppointmentRow | undefined {
  const pending = rows.filter(isPendingConfirmation)
  if (pending.length === 0) return undefined

  return pending.sort((a, b) => {
    const aReminder = a.reminder_sent === true ? 1 : 0
    const bReminder = b.reminder_sent === true ? 1 : 0
    if (aReminder !== bReminder) return bReminder - aReminder

    const aStarted = a.started_at ? Date.parse(a.started_at) : 0
    const bStarted = b.started_at ? Date.parse(b.started_at) : 0
    if (aStarted !== bStarted) return bStarted - aStarted

    const aAppt = a.appointment_start ? Date.parse(a.appointment_start) : 0
    const bAppt = b.appointment_start ? Date.parse(b.appointment_start) : 0
    return aAppt - bAppt
  })[0]
}

async function loadClientCalendarConfig(clientId: string): Promise<ClientCalendarConfig | null> {
  const { data, error } = await supabase
    .from('clients')
    .select('google_refresh_token, calendar_id')
    .eq('id', clientId)
    .maybeSingle()

  if (error) throw error
  return data
}

async function syncGoogleCalendar(
  rdv: AppointmentRow,
  action: 'confirmation' | 'annulation',
): Promise<string | null> {
  if (!rdv.google_event_id || !rdv.client_id) {
    return 'missing google_event_id or client_id'
  }

  const client = await loadClientCalendarConfig(rdv.client_id)
  if (!client?.google_refresh_token) {
    return 'missing google_refresh_token for client'
  }

  const calendarId = client.calendar_id || 'primary'
  if (action === 'confirmation') {
    await markAppointmentConfirmedInGoogleCalendar(
      client.google_refresh_token,
      calendarId,
      rdv.google_event_id,
    )
  } else {
    await markAppointmentCancelledInGoogleCalendar(
      client.google_refresh_token,
      calendarId,
      rdv.google_event_id,
    )
  }
  return null
}

const TWIML_EMPTY = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

serve(async (req) => {
  const debug: Record<string, unknown> = {
    received: 0,
    bodyMsg: '',
    rawFrom: '',
    cleanNumber: '',
    matches: 0,
    pending: 0,
    rdv_found: false,
    rdv_id: null,
    rdv_name: null,
    action: 'aucune',
    confirmed: false,
    cancelled: false,
    sms_sent: false,
    google_calendar_updated: false,
  }

  try {
    const text = await req.text()
    const params = new URLSearchParams(text)
    const form = Object.fromEntries(params.entries())

    const rawFrom = form.From?.toString() || ''
    const bodyMsg = (form.Body?.toString() || '').toUpperCase().trim()
    const cleanNumber = normalizePhone(rawFrom)

    debug.received = 1
    debug.bodyMsg = bodyMsg
    debug.rawFrom = rawFrom
    debug.cleanNumber = cleanNumber

    const { data: results, error: queryError } = await supabase
      .from('appels')
      .select(
        'id, client_id, google_event_id, appointment_name, appointment_number, caller_number, appointment_confirmed, appointment_cancelled, reminder_sent, started_at, appointment_start'
      )
      .eq('appointment_booked', true)
      .or(`appointment_number.ilike.%${cleanNumber}%,caller_number.ilike.%${cleanNumber}%`)
      .order('started_at', { ascending: false })
      .limit(20)

    if (queryError) {
      debug.query_error = queryError.message
      throw queryError
    }

    const rows = (results || []) as AppointmentRow[]
    debug.matches = rows.length
    debug.pending = rows.filter(isPendingConfirmation).length

    const rdv = pickPendingAppointment(rows)
    debug.rdv_found = !!rdv
    debug.rdv_id = rdv?.id ?? null
    debug.rdv_name = rdv?.appointment_name ?? null

    if (bodyMsg.includes('OUI') || bodyMsg.includes('YES') || bodyMsg.includes('CONFIRME')) {
      debug.action = 'confirmation'
      if (rdv) {
        const { error: updateError } = await supabase
          .from('appels')
          .update({ appointment_confirmed: true })
          .eq('id', rdv.id)

        if (updateError) {
          debug.update_error = updateError.message
        } else {
          debug.confirmed = true
          try {
            const googleError = await syncGoogleCalendar(rdv, 'confirmation')
            if (googleError) {
              debug.google_calendar_skip = googleError
            } else {
              debug.google_calendar_updated = true
            }
          } catch (googleError) {
            debug.google_calendar_error =
              googleError instanceof Error ? googleError.message : String(googleError)
          }

          await sendTwilioSms(
            rawFrom,
            `✅ Parfait ${rdv.appointment_name || ''} ! Votre rendez-vous est maintenant CONFIRMÉ. Merci !`
          )
          debug.sms_sent = true
        }
      }
    } else if (bodyMsg.includes('NON') || bodyMsg.includes('NO') || bodyMsg.includes('ANNULER')) {
      debug.action = 'annulation'
      if (rdv) {
        const { error: updateError } = await supabase
          .from('appels')
          .update({ appointment_cancelled: true })
          .eq('id', rdv.id)

        if (updateError) {
          debug.update_error = updateError.message
        } else {
          debug.cancelled = true
          try {
            const googleError = await syncGoogleCalendar(rdv, 'annulation')
            if (googleError) {
              debug.google_calendar_skip = googleError
            } else {
              debug.google_calendar_updated = true
            }
          } catch (googleError) {
            debug.google_calendar_error =
              googleError instanceof Error ? googleError.message : String(googleError)
          }

          await sendTwilioSms(rawFrom, `😔 Votre rendez-vous a été annulé. Merci pour votre réponse.`)
          debug.sms_sent = true
        }
      }
    }
  } catch (e) {
    debug.catch_error = e instanceof Error ? e.message : String(e)
  }

  if (DEBUG_MODE) {
    return new Response(JSON.stringify(debug, null, 2), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  return new Response(TWIML_EMPTY, {
    status: 200,
    headers: { 'Content-Type': 'text/xml' },
  })
})

async function sendTwilioSms(to: string, message: string) {
  await fetch(`https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`, {
    method: 'POST',
    headers: { Authorization: 'Basic ' + btoa(`${twilioSid}:${twilioToken}`) },
    body: new URLSearchParams({
      To: to.startsWith('+') ? to : `+1${to}`,
      From: fromNumber!,
      Body: message,
    }),
  })
}