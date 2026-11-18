import { Component, type ErrorInfo, type ReactNode } from 'react'

/**
 * Isola uma parte da tela: se ela quebrar (ex.: o módulo da análise não carregou depois de
 * uma versão nova), mostra a mensagem com "Recarregar a página" e o resto continua no ar.
 * Precisa ser classe: o React só pega erros de renderização com `componentDidCatch`.
 */
export class LimiteDeErro extends Component<{ mensagem: string; children: ReactNode }, { erro: boolean }> {
  state = { erro: false }

  static getDerivedStateFromError() {
    return { erro: true }
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error(erro, info.componentStack)
  }

  render() {
    if (!this.state.erro) return this.props.children
    return (
      <div className="recipiente limite-erro" role="alert">
        <p className="corpo-sm">{this.props.mensagem}</p>
        <button type="button" className="botao-recarregar" onClick={() => window.location.reload()}>
          Recarregar a página
        </button>
      </div>
    )
  }
}
