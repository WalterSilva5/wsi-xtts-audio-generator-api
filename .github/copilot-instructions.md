# Instruções rápidas para o Copilot neste repositório

Objetivo: orientar ações de refatoração, padronização e verificação mantendo retrocompatibilidade.

1) Papel geral
- Manter KubeManagementService como façade (retrocompatível). Todos os métodos públicos atuais devem continuar existindo e delegar para as novas classes.
- Extrair responsabilidades em serviços pequenos e coesos (ver seção "Novas classes").

2) Novas classes e responsabilidades (apenas estrutura)
- NodepoolService
  - Interações OCI/Container Engine relacionadas a nodepools.
  - Métodos: get_nodepool_names, get_nodepool_by_name, update_nodepool, handle_update_nodepool, update_nodepool_details, get_current_nodepool_size, delete_nodepool.
- PodService
  - Operações de pods: listagem por namespace/nodepool, formatação e deleção.
  - Métodos: list_nodepools_with_pods, list_pods_by_namespace, delete_pod_by_name, helpers de agrupamento.
- ScaleService (NodepoolScaler)
  - Lógica de dimensionamento e validações.
  - Métodos: start_scale_nodepool_intent (async), get_scale_variables, _is_valid_size_type, _calculate_new_size, _is_size_within_limits e logs auxiliares.
- ObserverAdapter
  - Encapsula/repassa chamadas para KubeObserverService (get_nodes, get_pods_with_names_in_nodepool, delete_nodepool etc.).
  - Mantém assinaturas usadas pelo façade.
- SubprocessExecutor
  - Centraliza chamadas a subprocess, parsing JSON e logging.
  - Métodos: run, run_output, run_json.
- PodParser / KubeCmdHelper
  - PodParser: parse_pods_json.
  - KubeCmdHelper: construir comandos kubectl padronizados.
- ConfigAccessor (ou usar Core)
  - Fornece env/logger de forma injetável.

3) Regras de compatibilidade
- Não alterar assinaturas públicas existentes. KubeManagementService deve delegar internamente.
- Métodos async devem manter comportamento (evitar uso de asyncio.run se já houver loop — detectar e criar task quando necessário).
- Preservar semáforos e mecanismos de concorrência existentes (ex.: active_nodes_semaphore).

4) Estilo e convenções
- Centralizar chamadas de subprocess em SubprocessExecutor (evita duplicação e melhora logs).
- Quebrar chamadas longas em múltiplas linhas (ex.: chamadas a oci.container_engine.models.UpdateNodePoolNodeConfigDetails).
- Evitar capturar Exception globalmente; se for necessário, registre explicitamente e re-raise quando apropriado. (Nota: .pylintrc atual tem W0718 desabilitado — use com cautela.)
- Usar PodParser para todo parsing JSON do kubectl.

5) Pylint e verificação estática
- .pylintrc mantém disables: C0114,C0115,C0116,W0718,R0903 e habilita E1101.
- Rodar manualmente:
  - pylint --rcfile=.pylintrc src/infrastructure/kubernetes/kube_management_service.py
- No VSCode: garanta python.linting.pylintEnabled=true e python.linting.pylintArgs=["--rcfile","${workspaceFolder}/.pylintrc"]

6) Testes e cobertura
- Escrever unit tests para:
  - Delegation do KubeManagementService (mocks das novas classes).
  - SubprocessExecutor.run_json (sucesso e falha no parse).
  - ScaleService: validações de limites e cálculo de novo tamanho.
  - PodParser.parse_pods_json.
- Tests async: use pytest-asyncio.

7) Checklist do PR
- Mantém assinaturas públicas e retrocompatibilidade.
- Logs suficientes em erros (executor/observer).
- Pylint rodando sem esconder E1101.
- Testes adicionados para lógica extraída.
- Atualizar diagrama UML (docs/xavier_xb_autoscale_uml.puml) se a estrutura mudar.

8) Comandos úteis
- Rodar linter: pylint --rcfile=.pylintrc src/
- Rodar testes: pytest -q
- Executar formatador/linters: black . && isort .

9) Observações finais
- Se encontrar falta de erros "método não existe", confirme .pylintrc está sendo usado e E1101 habilitado.
- Preferir injeção de dependências para facilitar mocks e testes.
- Manter mensagens de log claras e concisas; evitar logs duplicados.

Fim.