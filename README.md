# Task to Code

Este projeto automatiza o processo de transformar tasks do Jira em alterações de código usando o Aider e criar Pull Requests no GitHub. Ele utiliza IA para gerar código baseado nas especificações das tasks do Jira.

## Funcionalidades

- Leitura e processamento de tasks do Jira
- Geração inteligente de prompts para o Aider
- Execução de comandos do Aider com suporte a múltiplos modelos de IA
- Criação automática de Pull Requests no GitHub
- Gerenciamento automático de branches Git
- Suporte a múltiplos projetos e repositórios
- Tratamento automático de codificação de caracteres especiais
- Integração com OpenRouter para modelos de IA

## Requisitos

- Python 3.8+
- Git
- Conta no Jira
- Conta no GitHub
- Conta no OpenRouter (para modelos de IA)

## Configuração

1. Clone o repositório:
```bash
git clone [url-do-repositorio]
cd task-to-code
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente no arquivo `.env`:
```env
JIRA_URL=sua_url_do_jira
JIRA_EMAIL=seu_email
JIRA_API_TOKEN=seu_token
GITHUB_TOKEN=seu_token_do_github
GITHUB_USER=seu_usuario_github
OPENROUTER_API_KEY=sua_chave_do_openrouter
```

4. Configure o arquivo `config.yaml` com os padrões das tasks do Jira e configurações dos projetos:
```yaml
projects:
  PROJ1:
    repository: usuario/repositorio
    directory: /caminho/para/repositorio
    description: "Descrição do projeto"

github:
  base_branch: main
  pr_template: |
    # Descrição
    {description}

    # Alterações
    {changes}

    # Task Jira
    {jira_key}

openrouter:
  model: anthropic/claude-3-opus-20240229
  temperature: 0.7
  base_url: https://openrouter.ai/api/v1

aider:
  prompt_template: |
    Você é um assistente de programação especializado em {project}.
    {project_description}

    Tarefa: {title}

    Descrição:
    {description}

    Requisitos:
    {requirements}
```

## Uso

1. Execute o script principal:
```bash
python main.py
```

2. Digite a chave da task do Jira quando solicitado (ex: PROJ-123)

O script irá:
1. Ler a task do Jira
2. Verificar se o projeto está configurado
3. Fazer checkout e pull da branch base
4. Gerar um prompt para o Aider
5. Executar o Aider no contexto do projeto
6. Criar uma nova branch
7. Criar um Pull Request com as alterações
8. Comentar na task do Jira com o link do PR

## Estrutura do Projeto

- `main.py`: Script principal com a lógica core
- `config.yaml`: Configurações do projeto
- `type_definitions.py`: Definições de tipos TypeScript
- `requirements.txt`: Dependências do projeto

## Formato da Task do Jira

A task do Jira deve seguir o seguinte formato na descrição:

```
Tipo: [Feature/Bug/Improvement]
Projeto: [Nome do Projeto]

Descrição: 
[Descrição detalhada da task]

Objetivo:
- [Objetivo 1]
- [Objetivo 2]

Requisitos:
- [Requisito 1]
- [Requisito 2]

Critérios de Aceitação:
- [Critério 1]
- [Critério 2]
```

## Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Crie um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes. 