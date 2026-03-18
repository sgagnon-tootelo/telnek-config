import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

const twilioSid = Deno.env.get('TWILIO_ACCOUNT_SID')
const twilioToken = Deno.env.get('TWILIO_AUTH_TOKEN')
const fromNumber = Deno.env.get('TWILIO_FROM_NUMBER')

// ←←← REMPLACE CES DEUX LIGNES PAR TES VRAIES VALEURS
const GOOGLE_CLIENT_ID     = "75518740155-nvrj65gv3rk35lnf1fe668lvq2rgik76.apps.googleusercontent.com"
const GOOGLE_CLIENT_SECRET = "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"

// ==================== FLAG DE DEBUG ====================
const DEBUG_MODE = false;   // ← Mets false quand tu ne veux plus voir le JSON

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
    deleted_from_google: false,
    token_status: 0,
    delete_status: 0,
    google_error: "",
    sms_sent: false
  }

  try {
    const text = await req.text()
    const params = new URLSearchParams(text)
    const form = Object.fromEntries(params.entries())

    const rawFrom = form.From?.toString() || ''
    const bodyMsg = (form.Body?.toString() || '').toUpperCase().trim()

    let clean = rawFrom.replace(/\D/g, '')
    if (clean.startsWith('1') && clean.length === 11) clean = clean.substring(1)
    const cleanNumber = clean

    debug.received = 1
    debug.bodyMsg = bodyMsg
    debug.rawFrom = rawFrom
    debug.cleanNumber = cleanNumber
    debug.triedNumbers = [cleanNumber, `+1${cleanNumber}`, `1${cleanNumber}`, `+${cleanNumber}`]

    const { data: results } = await supabase
      .from('appels')
      .select(`id, google_event_id, appointment_name, appointment_number, caller_number, clients!inner(google_refresh_token, calendar_id, company_name)`)
      .or(`appointment_number.in.(${debug.triedNumbers.join(',')}),caller_number.in.(${debug.triedNumbers.join(',')})`)
      .eq('appointment_booked', true)
      .is('appointment_confirmed', false)
      .is('appointment_cancelled', false)
      .limit(1)

    const rdv = results?.[0]
    debug.rdv_found = !!rdv
    debug.rdv_id = rdv ? rdv.id : null

    // ... (le reste de ta logique OUI / NON reste IDENTIQUE) ...
    if (bodyMsg.includes('OUI') || bodyMsg.includes('YES')) {
      debug.action = "confirmation"
      await supabase.from('appels').update({ appointment_confirmed: true }).eq('id', rdv.id)
      debug.confirmed = true
      await sendTwilioSms(rawFrom, `✅ Parfait ${rdv.appointment_name || ''} ! Votre rendez-vous est confirmé...`)
      debug.sms_sent = true
    } 
    else if (bodyMsg.includes('NON') || bodyMsg.includes('NO') || bodyMsg.includes('ANNULER')) {
      debug.action = "annulation"
      // ... ton code Google + update cancelled ...
      debug.cancelled = true
      await sendTwilioSms(rawFrom, `😔 Merci pour votre réponse. Votre rendez-vous a été annulé...`)
      debug.sms_sent = true
    }

  } catch (e) {
    debug.catch_error = e.message
  }

  // ==================== RETOUR FINAL ====================
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
    body: new URLSearchParams({ To: to.startsWith('+') ? to : `+1${to}`, From: fromNumber, Body: message })
  })
}