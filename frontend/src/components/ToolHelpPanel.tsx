import { TOOL_HELP } from '../data/toolHelpContent'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wide">{title}</h4>
      {children}
    </div>
  )
}

function List({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="text-sm text-slate-400 flex gap-2">
          <span className="text-slate-600">•</span><span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export default function ToolHelpPanel({ toolKey, onClose }: { toolKey: string; onClose: () => void }) {
  const content = TOOL_HELP[toolKey]
  if (!content) return null

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-5"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between sticky top-0 bg-[#1a1d27] pb-2">
          <h3 className="text-lg font-bold text-white">{content.name}</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-xl leading-none">×</button>
        </div>

        <Section title="What is this feature?">
          <p className="text-sm text-slate-300">{content.whatIsIt}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Why traders use it: </span>{content.whyTradersUseIt}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">What it detects: </span>{content.whatItDetects}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Why it matters: </span>{content.whyItMatters}</p>
        </Section>

        <Section title="How does it work?">
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Calculation: </span>{content.calculationMethod}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Detection logic: </span>{content.detectionLogic}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">AI involvement: </span>{content.aiInvolvement}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Math concepts: </span>{content.mathConcepts}</p>
        </Section>

        <Section title="How to use it?">
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">When to enable: </span>{content.whenToEnable}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Interpreting signals: </span>{content.howToInterpret}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Confirming trades: </span>{content.howToConfirm}</p>
          <p className="text-sm text-slate-500 font-medium mt-2">Common mistakes:</p>
          <List items={content.commonMistakes} />
          <p className="text-sm text-slate-500 font-medium mt-2">Best practices:</p>
          <List items={content.bestPractices} />
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Recommended timeframe: </span>{content.recommendedTimeframe}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Recommended conditions: </span>{content.recommendedConditions}</p>
        </Section>

        <Section title="Real Example">
          <p className="text-sm text-slate-300 italic">"{content.realExample}"</p>
        </Section>

        <Section title="Professional Tips">
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">How institutions use it: </span>{content.institutionalUse}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">When it fails: </span>{content.whenItFails}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">When to avoid: </span>{content.whenToAvoid}</p>
          <p className="text-sm text-slate-400"><span className="text-slate-500 font-medium">Combine with: </span>{content.combineWith}</p>
        </Section>
      </div>
    </div>
  )
}
