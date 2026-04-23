import { Header } from './components/Header'
import { ModeloForm } from './components/ModeloForm'
import { ExternalLink } from 'lucide-react'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-10">

        {/* Intro */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">
            Gerar model.xml
          </h2>
          <p className="text-gray-400 text-sm leading-relaxed max-w-2xl">
            Preencha as configurações do evento abaixo. O script conecta ao Oracle,
            extrai os metadados via <code className="text-brand-400">column_configuration</code>,
            e gera o <code className="text-brand-400">model_final.xml</code> completo
            para o IBM Cognos Framework Manager.
          </p>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-3 text-xs text-brand-400 hover:text-brand-300 transition"
          >
            <ExternalLink className="w-3 h-3" />
            Ver documentação da API (Swagger)
          </a>
        </div>

        <ModeloForm />
      </main>

      <footer className="border-t border-gray-800 py-4 text-center text-xs text-gray-600">
        CPqD Antifraude — Cognos Model Generator · Desenvolvido por Lucas Pinto
      </footer>
    </div>
  )
}
