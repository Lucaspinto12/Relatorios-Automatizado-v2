import { useForm } from 'react-hook-form'
import { useState, useRef } from 'react'
import { Download, Loader2, Play, Upload, X, FileCode2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { ConfiguracaoEvento } from '../types'
import { gerarModeloComBase } from '../api/modeloApi'
import { FormField } from './FormField'

export function ModeloForm() {
  const [loading, setLoading] = useState(false)
  const [xmlGerado, setXmlGerado] = useState<Blob | null>(null)
  const [nomeArquivo, setNomeArquivo] = useState('')
  const [modelBase, setModelBase] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ConfiguracaoEvento>({
    defaultValues: {
      dsn: 'ocipgd01.aquarius.cpqd.com.br:1521/bd119i1',
      data_source: 'SAFO_UNICRED',
    },
  })

  const onSubmit = async (data: ConfiguracaoEvento) => {
    if (!modelBase) {
      toast.error('Selecione o arquivo model.xml base')
      return
    }

    setLoading(true)
    setXmlGerado(null)

    try {
      const blob = await gerarModeloComBase(data, modelBase)
      setXmlGerado(blob)
      setNomeArquivo(`model_${data.nome_cognos}.xml`)
      toast.success('model.xml gerado com sucesso!')
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Erro ao gerar o modelo'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!xmlGerado) return
    const url = URL.createObjectURL(xmlGerado)
    const a = document.createElement('a')
    a.href = url
    a.download = nomeArquivo
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.xml')) {
      toast.error('Selecione um arquivo .xml válido')
      return
    }
    setModelBase(file)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">

      {/* Upload do model.xml base */}
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6 space-y-3">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Arquivo Base
        </h2>
        <p className="text-xs text-gray-500">
          Selecione o <code className="text-brand-400">model.xml</code> base do projeto Cognos.
          O arquivo gerado será baseado nele.
        </p>

        <div
          onClick={() => fileInputRef.current?.click()}
          className={`
            flex items-center gap-4 p-4 rounded-lg border-2 border-dashed cursor-pointer transition
            ${modelBase
              ? 'border-green-600 bg-green-950/30'
              : 'border-gray-700 hover:border-brand-500 hover:bg-gray-800/50'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xml"
            className="hidden"
            onChange={handleFileChange}
          />

          {modelBase ? (
            <>
              <FileCode2 className="w-8 h-8 text-green-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-green-300 truncate">{modelBase.name}</p>
                <p className="text-xs text-gray-500">
                  {(modelBase.size / 1024 / 1024).toFixed(1)} MB — clique para trocar
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setModelBase(null) }}
                className="text-gray-500 hover:text-red-400 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <Upload className="w-8 h-8 text-gray-500 shrink-0" />
              <div>
                <p className="text-sm text-gray-300">Clique para selecionar o model.xml</p>
                <p className="text-xs text-gray-500">Apenas arquivos .xml</p>
              </div>
            </>
          )}
        </div>
      </section>

      {/* Credenciais Oracle */}
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Credenciais Oracle
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField
            label="Usuário"
            placeholder="SAFPOC542_SCH"
            required
            error={errors.user?.message}
            {...register('user', { required: 'Obrigatório' })}
          />
          <FormField
            label="Senha"
            type="password"
            placeholder="••••••••"
            required
            error={errors.password?.message}
            {...register('password', { required: 'Obrigatório' })}
          />
        </div>
        <FormField
          label="DSN"
          placeholder="host:porta/servico"
          required
          hint="Ex: ocipgd01.aquarius.cpqd.com.br:1521/bd119i1"
          error={errors.dsn?.message}
          {...register('dsn', { required: 'Obrigatório' })}
        />
      </section>

      {/* Configurações do Evento */}
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Configurações do Evento
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField
            label="Nome da View Oracle"
            placeholder="VW_EVENT_UNI_CASH_IN"
            required
            hint="Nome da view no banco de dados"
            error={errors.nome_view?.message}
            {...register('nome_view', { required: 'Obrigatório' })}
          />
          <FormField
            label="Nome Técnico (Cognos)"
            placeholder="EVENT_UNI_CASH_IN"
            required
            hint="Identificador técnico no Framework Manager"
            error={errors.nome_cognos?.message}
            {...register('nome_cognos', { required: 'Obrigatório' })}
          />
          <FormField
            label="Nome de Negócio"
            placeholder="Cash-In"
            required
            hint="Usado nas namespaces da Presentation View"
            error={errors.nome_negocio?.message}
            {...register('nome_negocio', { required: 'Obrigatório' })}
          />
          <FormField
            label="Fonte de Dados"
            placeholder="SAFO_UNICRED"
            required
            hint="Nome da data source no Cognos"
            error={errors.data_source?.message}
            {...register('data_source', { required: 'Obrigatório' })}
          />
        </div>
        <FormField
          label="Campo de Valor (VL_EVENT)"
          placeholder="VL_OPERACAO"
          hint="Coluna da view para alias VL_EVENT no SQL. Deixe vazio para não incluir."
          {...register('vl_event_campo')}
        />
      </section>

      {/* Ações */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <button
          type="submit"
          disabled={loading || !modelBase}
          className="
            flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-sm
            bg-brand-600 hover:bg-brand-700 text-white transition
            disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto
          "
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {loading ? 'Gerando...' : 'Gerar model.xml'}
        </button>

        {xmlGerado && (
          <button
            type="button"
            onClick={handleDownload}
            className="
              flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-sm
              bg-green-600 hover:bg-green-700 text-white transition
              w-full sm:w-auto
            "
          >
            <Download className="w-4 h-4" />
            Baixar {nomeArquivo}
          </button>
        )}
      </div>

    </form>
  )
}
