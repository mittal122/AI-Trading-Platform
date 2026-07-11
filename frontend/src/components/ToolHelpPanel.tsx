import { X } from 'lucide-react'
import { TOOL_HELP } from '../data/toolHelpContent'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <h4 className="panel-title">{title}</h4>
      {children}
    </div>
  )
}

function List({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1 list-disc ml-4">
      {items.map((item, i) => (
        <li key={i} className="text-[12.5px] text-fg-soft">{item}</li>
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
        className="bg-surface border border-line rounded-lg max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-5"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between sticky top-0 bg-surface pb-2">
          <h3 className="text-[15px] font-semibold text-fg">{content.name}</h3>
          <button onClick={onClose} aria-label="Close" className="text-fg-faint hover:text-fg cursor-pointer">
            <X size={16} />
          </button>
        </div>

        <Section title="What is this feature?">
          <p className="text-[12.5px] text-fg-soft">{content.whatIsIt}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Why traders use it: </span>{content.whyTradersUseIt}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">What it detects: </span>{content.whatItDetects}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Why it matters: </span>{content.whyItMatters}</p>
        </Section>

        <Section title="How does it work?">
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Calculation: </span>{content.calculationMethod}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Detection logic: </span>{content.detectionLogic}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">AI involvement: </span>{content.aiInvolvement}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Math concepts: </span>{content.mathConcepts}</p>
        </Section>

        <Section title="How to use it?">
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">When to enable: </span>{content.whenToEnable}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Interpreting signals: </span>{content.howToInterpret}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Confirming trades: </span>{content.howToConfirm}</p>
          <p className="text-[12.5px] text-fg-faint font-medium mt-2">Common mistakes:</p>
          <List items={content.commonMistakes} />
          <p className="text-[12.5px] text-fg-faint font-medium mt-2">Best practices:</p>
          <List items={content.bestPractices} />
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Recommended timeframe: </span>{content.recommendedTimeframe}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Recommended conditions: </span>{content.recommendedConditions}</p>
        </Section>

        <Section title="Real Example">
          <p className="text-[12.5px] text-fg-soft italic">"{content.realExample}"</p>
        </Section>

        <Section title="Professional Tips">
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">How institutions use it: </span>{content.institutionalUse}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">When it fails: </span>{content.whenItFails}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">When to avoid: </span>{content.whenToAvoid}</p>
          <p className="text-[12.5px] text-fg-soft"><span className="text-fg-faint font-medium">Combine with: </span>{content.combineWith}</p>
        </Section>
      </div>
    </div>
  )
}
