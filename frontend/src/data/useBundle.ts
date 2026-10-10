import { useEffect, useMemo, useState } from 'react'
import { loadBundle, replayDate } from './client'
import type { Bundle } from './types'
import { decodeFrames } from '../lib/frames'

export function useBundle() {
  const [bundle, setBundle] = useState<Bundle | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    loadBundle(replayDate()).then(b => alive && setBundle(b)).catch(e => alive && setError(String(e)))
    return () => { alive = false }
  }, [])
  const frames = useMemo(() => (bundle ? decodeFrames(bundle.smoke) : []), [bundle])
  return { bundle, frames, error }
}
