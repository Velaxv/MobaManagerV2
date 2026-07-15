import { describe, expect, it } from 'vitest'
import {
  countAliveTowers,
  flashAnchor,
  locationLabel,
  parseLocationFromEvent,
  resolveStructures,
  RIFT_STRUCTURE_DEFS,
} from './riftMap'

describe('parseLocationFromEvent', () => {
  it('usa location explícita', () => {
    expect(parseLocationFromEvent({ location: 'DRAGON' })).toBe('DRAGON')
  })

  it('infere dragão pelo tipo/texto', () => {
    expect(parseLocationFromEvent({ eventType: 'DRAGON_SECURED' })).toBe('DRAGON')
    expect(parseLocationFromEvent({ text: 'time blue pega o dragão' })).toBe('DRAGON')
  })

  it('infere baron e lanes de torre', () => {
    expect(parseLocationFromEvent({ eventType: 'BARON_SECURED' })).toBe('BARON')
    expect(
      parseLocationFromEvent({
        eventType: 'TURRET_DESTROYED',
        text: 'torre top destruída',
      }),
    ).toBe('TOP_LANE')
    expect(
      parseLocationFromEvent({
        eventType: 'SOLO_KILL',
        role: 'MID',
      }),
    ).toBe('MID_LANE')
  })

  it('retorna null sem pista', () => {
    expect(parseLocationFromEvent(null)).toBeNull()
    expect(parseLocationFromEvent({})).toBeNull()
  })
})

describe('locationLabel', () => {
  it('traduz chaves conhecidas', () => {
    expect(locationLabel('TOP_LANE')).toBe('Top')
    expect(locationLabel('DRAGON')).toBe('Dragão')
    expect(locationLabel('BARON')).toBe('Baron')
  })

  it('fallback para string crua', () => {
    expect(locationLabel('CUSTOM_SPOT')).toBe('CUSTOM_SPOT')
    expect(locationLabel(null)).toBe('')
  })
})

describe('resolveStructures + countAliveTowers', () => {
  it('começa com todas as torres vivas', () => {
    const structs = resolveStructures([])
    expect(structs.length).toBe(RIFT_STRUCTURE_DEFS.length)
    const counts = countAliveTowers(structs)
    expect(counts.blue).toBe(9)
    expect(counts.red).toBe(9)
  })

  it('derruba torre do oponente em TURRET_DESTROYED', () => {
    const structs = resolveStructures([
      { eventType: 'TURRET_DESTROYED', side: 'BLUE', text: 'torre mid' },
    ])
    const counts = countAliveTowers(structs)
    expect(counts.red).toBe(8)
    expect(counts.blue).toBe(9)
  })

  it('vitória derruba estruturas do perdedor', () => {
    const structs = resolveStructures([], null, 'BLUE', true)
    const counts = countAliveTowers(structs)
    expect(counts.red).toBe(0)
    expect(counts.blue).toBe(9)
  })
})

describe('flashAnchor', () => {
  it('mapeia objetivos e lanes', () => {
    expect(flashAnchor('DRAGON')).toEqual({ x: 58, y: 66 })
    expect(flashAnchor('TOP_LANE').x).toBeLessThan(50)
    expect(flashAnchor(null)).toEqual({ x: 50, y: 50 })
  })
})
