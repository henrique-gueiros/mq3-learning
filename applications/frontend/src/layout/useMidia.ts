import { useSyncExternalStore } from 'react'

/** `true` enquanto a media query vale (ex.: `'(max-width: 640px)'`); acompanha o redimensionamento. */
export function useMidia(consulta: string): boolean {
  return useSyncExternalStore(
    (avisar) => {
      const m = window.matchMedia?.(consulta)
      m?.addEventListener('change', avisar)
      return () => m?.removeEventListener('change', avisar)
    },
    () => window.matchMedia?.(consulta).matches ?? false,
  )
}
