type CalendarEvent = {
  summary?: string
  description?: string
  status?: string
}

async function refreshAccessToken(refreshToken: string): Promise<string> {
  const clientId = Deno.env.get('GOOGLE_CLIENT_ID')
  const clientSecret = Deno.env.get('GOOGLE_CLIENT_SECRET')
  if (!clientId || !clientSecret) {
    throw new Error('GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured')
  }

  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      refresh_token: refreshToken,
      grant_type: 'refresh_token',
    }),
  })

  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.error_description || payload.error || 'Google token refresh failed')
  }
  return payload.access_token as string
}

async function getCalendarEvent(
  calendarId: string,
  eventId: string,
  accessToken: string,
): Promise<CalendarEvent> {
  const response = await fetch(
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  )
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Google Calendar get failed: ${detail}`)
  }
  return await response.json()
}

async function patchCalendarEvent(
  calendarId: string,
  eventId: string,
  accessToken: string,
  body: CalendarEvent,
): Promise<void> {
  const response = await fetch(
    `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    },
  )
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Google Calendar patch failed: ${detail}`)
  }
}

function stripStatusPrefix(summary: string): string {
  return summary
    .replace(/^✅\s*Confirmé\s*[—-]\s*/i, '')
    .replace(/^❌\s*Annulé\s*[—-]\s*/i, '')
    .trim()
}

function confirmationNote(): string {
  const when = new Date().toLocaleString('fr-CA', { timeZone: 'America/Montreal' })
  return `Confirmé par SMS le ${when}.`
}

function cancellationNote(): string {
  const when = new Date().toLocaleString('fr-CA', { timeZone: 'America/Montreal' })
  return `Annulé par SMS le ${when}.`
}

function appendNote(description: string | undefined, note: string): string {
  const base = (description || '').trim()
  if (!base) return note
  if (base.includes(note.split(' le ')[0])) return base
  return `${base}\n\n${note}`
}

export async function markAppointmentConfirmedInGoogleCalendar(
  refreshToken: string,
  calendarId: string,
  eventId: string,
): Promise<void> {
  const accessToken = await refreshAccessToken(refreshToken)
  const event = await getCalendarEvent(calendarId, eventId, accessToken)
  const baseSummary = stripStatusPrefix(event.summary || 'Rendez-vous')
  await patchCalendarEvent(calendarId, eventId, accessToken, {
    summary: `✅ Confirmé — ${baseSummary}`,
    description: appendNote(event.description, confirmationNote()),
    status: 'confirmed',
  })
}

export async function markAppointmentCancelledInGoogleCalendar(
  refreshToken: string,
  calendarId: string,
  eventId: string,
): Promise<void> {
  const accessToken = await refreshAccessToken(refreshToken)
  const event = await getCalendarEvent(calendarId, eventId, accessToken)
  const baseSummary = stripStatusPrefix(event.summary || 'Rendez-vous')
  await patchCalendarEvent(calendarId, eventId, accessToken, {
    summary: `❌ Annulé — ${baseSummary}`,
    description: appendNote(event.description, cancellationNote()),
    status: 'cancelled',
  })
}