import { useState } from 'react'
import { Info } from 'lucide-react'
import { TOOL_HELP, TOOL_HELP_ORDER } from '../data/toolHelpContent'
import ToolHelpPanel from './ToolHelpPanel'

export default function ToolToggleBar({ enabled, onToggle, loading, readyKeys }: {
  enabled: Set<string>
  onToggle: (key: string) => void
  /** true while a scan for the currently-enabled tools is in flight */
  loading: boolean
  /** tool keys with a result already back from the last completed scan */
  readyKeys: Set<string>
}) {
  const [helpKey, setHelpKey] = useState<string | null>(null)

  return (
    <div className="flex flex-wrap gap-2">
      {TOOL_HELP_ORDER.map(key => {
        const isOn = enabled.has(key)
        const isReady = isOn && readyKeys.has(key)
        const isPending = isOn && !isReady
        const name = TOOL_HELP[key]?.name ?? key
        return (
          <div key={key}
            className={`flex items-center gap-1 rounded-md border text-xs transition-colors ${
              isOn ? 'bg-accent-soft text-accent border-accent/40' : 'bg-bg border-line text-fg-soft'
            }`}>
            <button onClick={() => onToggle(key)}
              className="pl-3 pr-1.5 py-1.5 font-medium hover:text-fg flex items-center gap-1.5 cursor-pointer">
              {isOn && (
                <span
                  title={isPending ? 'Scanning…' : 'Live'}
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    isPending && loading ? 'bg-accent animate-pulse' : isReady ? 'bg-up' : 'bg-accent'
                  }`}
                />
              )}
              {name}
            </button>
            <button
              onClick={() => setHelpKey(key)}
              title={`About ${name}`}
              aria-label={`About ${name}`}
              className="pr-2 text-fg-faint hover:text-accent cursor-pointer"
            >
              <Info size={11} />
            </button>
          </div>
        )
      })}
      {helpKey && <ToolHelpPanel toolKey={helpKey} onClose={() => setHelpKey(null)} />}
    </div>
  )
}
