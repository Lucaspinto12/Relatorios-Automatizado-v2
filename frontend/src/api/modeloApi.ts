import axios from 'axios'
import { ConfiguracaoEvento } from '../types'

const api = axios.create({
  baseURL: '/modelo',
})

export async function gerarModelo(config: ConfiguracaoEvento): Promise<Blob> {
  const response = await api.post('/gerar', config, {
    responseType: 'blob',
  })
  return response.data
}

export async function gerarModeloComBase(
  config: ConfiguracaoEvento,
  modelBase: File
): Promise<Blob> {
  const formData = new FormData()
  formData.append('configuracao', JSON.stringify(config))
  formData.append('model_base', modelBase)

  const response = await api.post('/gerar-com-base', formData, {
    responseType: 'blob',
  })
  return response.data
}
