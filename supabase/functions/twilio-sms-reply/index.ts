import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

const twilioSid = Deno.env.get('TWILIO_ACCOUNT_SID')
const twilioToken = Deno.env.get('TWILIO_AUTH_TOKEN')
const fromNumber = Deno.env.get('TWILIO_FROM_NUMBER')

const DEBUG_MODE = false;   // ← Mets à false quand tu ne veux plus voir le debug

serve(async (req) => {
  const debug: any = {
    received: 0,
    bodyMsg: "",
    rawFrom: "",
    cleanNumber: "",
    triedNumbers: [],
    rdv_found: false,
    rdv_id: null,
    action: "aucune",
    confirmed: false,
    cancelled: false,
    sms_sent: false
  }

  try {
    const text = await req.text()
    const params = new URLSearchParams(text)
    const form = Object.fromEntries(params.entries())

    const rawFrom = form.From?.toString() || ''
    const bodyMsg = (form.Body?.toString() || '').toUpperCase().trim()

    // Nettoyage ultra-robuste du numéro entrant
    let clean = rawFrom.replace(/\D/g, '')
    if (clean.startsWith('1') && clean.length === 11) clean = clean.substring(1)
    const cleanNumber = clean   // ex: 5149474976

    debug.received = 1
    debug.bodyMsg = bodyMsg
    debug.rawFrom = rawFrom
    debug.cleanNumber = cleanNumber
    debug.triedNumbers = [cleanNumber, `+1${cleanNumber}`, `1${cleanNumber}`, `+${cleanNumber}`]

    // Recherche plus permissive (on cherche aussi les numéros sans +1)
    const { data: results } = await supabase
      .from('appels')
      .select(`id, google_event_id, appointment_name, appointment_number, caller_number`)
      .or(`appointment_number.ilike.%${cleanNumber}%,caller_number.ilike.%${cleanNumber}%`)
      .eq('appointment_booked', true)
      .or('appointment_confirmed.is.null,appointment_confirmed.eq.false')
      .or('appointment_cancelled.is.null,appointment_cancelled.eq.false')
      .limit(1)

    const rdv = results?.[0]
    debug.rdv_found = !!rdv
    debug.rdv_id = rdv ? rdv.id : null

    if (bodyMsg.includes('OUI') || bodyMsg.includes('YES') || bodyMsg.includes('CONFIRME')) {
      debug.action = "confirmation"
      if (rdv) {
        await supabase.from('appels')
          .update({ appointment_confirmed: true })
          .eq('id', rdv.id)
        debug.confirmed = true

        await sendTwilioSms(rawFrom, `✅ Parfait ${rdv.appointment_name || ''} ! Votre rendez-vous est maintenant CONFIRMÉ. Merci !`)
        debug.sms_sent = true
      }
    } 
    else if (bodyMsg.includes('NON') || bodyMsg.includes('NO') || bodyMsg.includes('ANNULER')) {
      debug.action = "annulation"
      if (rdv) {
        await supabase.from('appels')
          .update({ appointment_cancelled: true })
          .eq('id', rdv.id)
        debug.cancelled = true

        await sendTwilioSms(rawFrom, `😔 Votre rendez-vous a été annulé. Merci pour votre réponse.`)
        debug.sms_sent = true
      }
    }

  } catch (e) {
    debug.catch_error = e.message
  }

  if (DEBUG_MODE) {
    return new Response(JSON.stringify(debug, null, 2), { status: 200 })
  } else {
    return new Response("OK", { status: 200 })
  }
})

async function sendTwilioSms(to: string, message: string) {
  await fetch(`https://api.twilio.com/2010-04-01/Accounts/${twilioSid}/Messages.json`, {
    method: 'POST',
    headers: { 'Authorization': 'Basic ' + btoa(`${twilioSid}:${twilioToken}`) },
    body: new URLSearchParams({ 
      To: to.startsWith('+') ? to : `+1${to}`, 
      From: fromNumber, 
      Body: message 
    })
  })
}