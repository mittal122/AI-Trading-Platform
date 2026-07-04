import { useState } from 'react'
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
            className={`flex items-center gap-1 rounded-lg border text-xs transition-colors ${
              isOn ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300' : 'bg-[#0f1117] border-[#2a2d3e] text-slate-400'
            }`}>
            <button onClick={() => onToggle(key)} className="pl-3 pr-1.5 py-1.5 font-medium hover:text-white flex items-center gap-1.5">
              {isOn && (
                <span
                  title={isPending ? 'Scanning…' : 'Live'}
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    isPending && loading ? 'bg-amber-400 animate-pulse' : isReady ? 'bg-green-400' : 'bg-amber-400'
                  }`}
                />
              )}
              {name}
            </button>
            <button
              onClick={() => setHelpKey(key)}
              title={`About ${name}`}
              className="pr-2 text-slate-500 hover:text-indigo-400"
            >
              ⓘ
            </button>
          </div>
        )
      })}
      {helpKey && <ToolHelpPanel toolKey={helpKey} onClose={() => setHelpKey(null)} />}
    </div>
  )
}
