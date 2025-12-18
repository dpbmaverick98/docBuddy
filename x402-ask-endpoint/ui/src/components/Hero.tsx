interface HeroProps {}

export default function Hero({}: HeroProps) {
  return (
    <div className="text-center mb-12">
      <h1 className="text-6xl font-bold text-primary mb-4 tracking-tight">
        docsBuddy <span className="text-white">ask402</span>
      </h1>
      <p className="text-xl text-gray-400">
        AI-powered Q&A for documentation with x402 payments
      </p>
    </div>
  )
}