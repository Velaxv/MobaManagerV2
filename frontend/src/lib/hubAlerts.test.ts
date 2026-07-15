import { describe, expect, it } from 'vitest'
import { badgeForScreen, buildHubAlerts } from './hubAlerts'

describe('buildHubAlerts', () => {
  it('prioriza critical sobre warning', () => {
    const alerts = buildHubAlerts({
      burnoutCount: 1,
      matchPending: true,
      matchLive: false,
      financeHealth: 'warning',
    })
    expect(alerts[0].id).toBe('match-draft')
    expect(alerts[0].level).toBe('critical')
    expect(alerts.some((a) => a.id === 'burnout')).toBe(true)
  })

  it('demissão é critical', () => {
    const alerts = buildHubAlerts({
      burnoutCount: 0,
      matchPending: false,
      matchLive: false,
      boardFired: true,
      boardMessage: 'Fired',
    })
    expect(alerts[0].id).toBe('fired')
  })

  it('sem alertas quando tudo ok', () => {
    expect(
      buildHubAlerts({
        burnoutCount: 0,
        matchPending: false,
        matchLive: false,
        boardOnTrack: true,
        financeHealth: 'healthy',
      }),
    ).toHaveLength(0)
  })
})

describe('badgeForScreen', () => {
  it('TRAINING mostra contagem de burnout', () => {
    const b = badgeForScreen('TRAINING', {
      burnoutCount: 2,
      matchPending: false,
      matchLive: false,
    })
    expect(b?.show).toBe(true)
    expect(b?.count).toBe(2)
  })

  it('DRAFT só com match pending', () => {
    expect(
      badgeForScreen('DRAFT', {
        burnoutCount: 0,
        matchPending: false,
        matchLive: false,
      }),
    ).toBeNull()
    expect(
      badgeForScreen('DRAFT', {
        burnoutCount: 0,
        matchPending: true,
        matchLive: false,
      })?.tone,
    ).toBe('critical')
  })
})
