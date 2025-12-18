interface EndpointSelectorProps {
  selected: 'privy' | 'polymarket'
  onSelect: (endpoint: 'privy' | 'polymarket') => void
}

export default function EndpointSelector({ selected, onSelect }: EndpointSelectorProps) {
  return (
    <div className="flex justify-center gap-6 mb-8">
      <button
        type="button"
        onClick={() => onSelect('privy')}
        className={`px-8 py-4 rounded-lg font-semibold text-lg transition-all ${
          selected === 'privy'
            ? 'bg-primary text-white shadow-lg shadow-purple-900/50 transform scale-105'
            : 'bg-surface text-gray-400 border border-border hover:border-primary hover:text-white'
        }`}
      >
        ask/privy
      </button>
      <button
        type="button"
        onClick={() => onSelect('polymarket')}
        className={`px-8 py-4 rounded-lg font-semibold text-lg transition-all ${
          selected === 'polymarket'
            ? 'bg-primary text-white shadow-lg shadow-purple-900/50 transform scale-105'
            : 'bg-surface text-gray-400 border border-border hover:border-primary hover:text-white'
        }`}
      >
        ask/polymarket
      </button>
    </div>
  )
}