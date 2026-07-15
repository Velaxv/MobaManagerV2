import { describe, expect, it } from 'vitest'
import { getOrgBrand, orgPrimary, ALL_ORG_BRANDS } from './orgBrands'

describe('orgBrands', () => {
  it('tem as 8 orgs do CBLOL 2026', () => {
    expect(ALL_ORG_BRANDS).toHaveLength(8)
    const tags = ALL_ORG_BRANDS.map((b) => b.tag).sort()
    expect(tags).toEqual(['FUR', 'FX7', 'LEV', 'LLL', 'LOS', 'PNG', 'RED', 'VKS'].sort())
  })

  it('resolve por tag', () => {
    expect(getOrgBrand('PNG').primary).toBeTruthy()
    expect(getOrgBrand('lll').tag).toBe('LLL')
    expect(getOrgBrand('FUR').name).toMatch(/FURIA/i)
  })

  it('resolve por nome de time', () => {
    expect(getOrgBrand('paiN Gaming').tag).toBe('PNG')
    expect(getOrgBrand('LOUD').tag).toBe('LLL')
    expect(getOrgBrand('FURIA Esports').tag).toBe('FUR')
  })

  it('fallback seguro', () => {
    const b = getOrgBrand(null)
    expect(b.primary).toBeTruthy()
    expect(orgPrimary('UNKNOWN_ORG')).toBeTruthy()
  })
})
