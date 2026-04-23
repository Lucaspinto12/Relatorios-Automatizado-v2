import { FileCode2 } from 'lucide-react'

export function Header() {
  return (
    <header className="border-b border-gray-800 bg-gray-900">
      <div className="mx-auto max-w-5xl px-6 py-4 flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-brand-600">
          <FileCode2 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-white leading-tight">
            Cognos Model Generator
          </h1>
          <p className="text-xs text-gray-400">
            Geração automática do model.xml — CPqD Antifraude
          </p>
        </div>
      </div>
    </header>
  )
}
