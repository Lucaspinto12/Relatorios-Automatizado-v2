export interface ConfiguracaoEvento {
  user: string
  password: string
  dsn: string
  nome_view: string
  nome_cognos: string
  nome_negocio: string
  data_source: string
  vl_event_campo?: string
}
