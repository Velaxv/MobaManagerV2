import { describe, expect, it } from 'vitest'
import {
  applyTowerHpFromPressure,
  buildHeatmapPoints,
  buildMiniFeed,
  countAliveTowers,
  eventTypeGlyph,
  flashAnchor,
  locationLabel,
  parseLocationFromEvent,
  resolveObjectiveContest,
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

describe('buildHeatmapPoints', () => {
  it('retorna vazio sem eventos', () => {
    expect(buildHeatmapPoints([])).toEqual([])
  })

  it('agrega kills e objetivos em pontos normalizados', () => {
    const pts = buildHeatmapPoints([
      { eventType: 'SOLO_KILL', location: 'MID_LANE', side: 'BLUE', intensity: 1, role: 'MID' },
      { eventType: 'DRAGON_SECURED', location: 'DRAGON', side: 'BLUE', intensity: 0.9 },
      { eventType: 'TURRET_DESTROYED', location: 'BOT_LANE', side: 'RED', intensity: 0.8, role: 'BOT' },
      { eventType: 'FARM', location: 'TOP_LANE', side: 'BLUE', intensity: 0.4, role: 'TOP' },
    ])
    expect(pts.length).toBeGreaterThanOrEqual(3)
    for (const p of pts) {
      expect(p.x).toBeGreaterThanOrEqual(6)
      expect(p.x).toBeLessThanOrEqual(94)
      expect(p.y).toBeGreaterThanOrEqual(6)
      expect(p.y).toBeLessThanOrEqual(94)
      expect(p.weight).toBeGreaterThan(0)
      expect(p.weight).toBeLessThanOrEqual(1.001)
    }
    // kill/objective deve pesar mais que farm
    const farm = pts.find((p) => p.kind?.includes('FARM'))
    const heavy = pts[0]
    expect(heavy.weight).toBeGreaterThanOrEqual(farm?.weight ?? 0)
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

describe('applyTowerHpFromPressure (ME-7)', () => {
  it('marca torre Red T1 sob siege com pressão Blue alta no mid', () => {
    const base = resolveStructures([])
    const withHp = applyTowerHpFromPressure(base, { TOP: 0, MID: 40, BOT: 0 })
    const redMidT1 = withHp.find((s) => s.id === 'RED_MID_T1')
    expect(redMidT1?.underSiege).toBe(true)
    expect(redMidT1?.hp).toBeDefined()
    expect(redMidT1!.hp!).toBeLessThan(100)
    expect(redMidT1!.hp!).toBeGreaterThan(0)
    const blueMidT1 = withHp.find((s) => s.id === 'BLUE_MID_T1')
    expect(blueMidT1?.underSiege).toBe(false)
    expect(blueMidT1?.hp).toBe(100)
  })

  it('sem pressão: HP cheio e sem siege', () => {
    const base = resolveStructures([])
    const withHp = applyTowerHpFromPressure(base, { TOP: 0, MID: 0, BOT: 0 })
    expect(withHp.every((s) => !s.underSiege)).toBe(true)
  })
})

describe('resolveObjectiveContest (ME-7)', () => {
  it('ativa contest no mid game', () => {
    const c = resolveObjectiveContest('MID_GAME', 12, null, [])
    expect(c.kind).toBe('DRAGON')
    expect(c.active).toBe(true)
    expect(c.bluePct + c.redPct).toBe(100)
  })

  it('secure de dragão favorece o lado do evento', () => {
    const c = resolveObjectiveContest('MID_GAME', 14, {
      eventType: 'DRAGON_SECURED',
      side: 'BLUE',
      text: 'Blue assegura o dragão',
    })
    expect(c.kind).toBe('DRAGON')
    expect(c.bluePct).toBeGreaterThan(c.redPct)
    expect(c.leading).toBe('BLUE')
  })

  it('late favorece baron', () => {
    const c = resolveObjectiveContest('LATE_GAME', 28, null, [])
    expect(c.kind).toBe('BARON')
  })
})

describe('buildMiniFeed + glyph', () => {
  it('retorna os mais recentes primeiro e limita', () => {
    const feed = buildMiniFeed(
      [
        { text: 'primeiro evento longo o suficiente', timestamp: '01:00' },
        { text: 'segundo evento longo o suficiente', timestamp: '02:00' },
        { text: 'terceiro evento longo o suficiente', timestamp: '03:00' },
        { text: 'quarto evento longo o suficiente', timestamp: '04:00' },
        { text: 'quinto evento longo o suficiente', timestamp: '05:00' },
      ],
      3,
    )
    expect(feed).toHaveLength(3)
    expect(feed[0].text).toContain('quinto')
    expect(feed[2].text).toContain('terceiro')
  })

  it('glyph por tipo', () => {
    expect(eventTypeGlyph('DRAGON_SECURED')).toBe('🐉')
    expect(eventTypeGlyph('TURRET_DESTROYED')).toBe('🏰')
    expect(eventTypeGlyph('SOLO_KILL')).toBe('⚔')
  })
})
