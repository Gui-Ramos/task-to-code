import os
from typing import Any, Dict, Optional

import ftfy
import yaml
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from dotenv import load_dotenv
from git import Repo
from github import Github
from jira import JIRA

from type_definitions import Config, Task


class TaskToCode:
    def __init__(self) -> None:
        load_dotenv()
        self.config: Config = self.load_config()
        self.jira: JIRA = self.setup_jira()
        self.github: Github = self.setup_github()
        self.repo: Any = None  # Type from PyGithub

    def load_config(self) -> Config:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def setup_jira(self) -> JIRA:
        return JIRA(
            server=os.getenv('JIRA_URL'),
            basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
        )

    def setup_github(self) -> Github:
        return Github(os.getenv('GITHUB_TOKEN'))

    def get_project_repo(self, project: str) -> Any:
        """Obtém o repositório do GitHub para um projeto específico."""
        project_config = self.config['projects'][project]
        return self.github.get_repo(project_config['repository'])

    def parse_description_fields(self, description: str) -> Dict[str, str]:
        """Extrai os campos da descrição da task."""
        fields = {}
        current_field = None
        current_content = []

        for line in description.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Verifica se a linha é um cabeçalho de campo
            if ':' in line:
                # Se já estávamos processando um campo, salva ele
                if current_field:
                    fields[current_field] = '\n'.join(current_content).strip()
                    current_content = []
                
                # Divide a linha no primeiro ':'
                field_name, field_value = line.split(':', 1)
                field_name = field_name.strip()
                field_value = field_value.strip()
                
                # Se o valor não está vazio, salva o campo imediatamente
                if field_value:
                    fields[field_name] = field_value
                else:
                    current_field = field_name
            elif current_field:
                current_content.append(line)

        # Salva o último campo
        if current_field and current_content:
            fields[current_field] = '\n'.join(current_content).strip()

        return fields

    def get_jira_task(self, task_key: str) -> Task:
        """Obtém os detalhes de uma task do Jira."""
        issue = self.jira.issue(task_key)
        
        # Extrai os campos da descrição e corrige a codificação
        description = issue.fields.description
        if isinstance(description, bytes):
            description = description.decode('utf-8')
        description = ftfy.fix_text(description)
        
        fields = self.parse_description_fields(description)
        
        return {
            'key': issue.key,
            'title': ftfy.fix_text(issue.fields.summary),
            'description': description,
            'type': fields.get('Tipo', ''),
            'project': fields.get('Projeto', ''),
            'fields': fields
        }

    def generate_aider_prompt(self, task: Task) -> str:
        """Gera o prompt para o Aider baseado na task do Jira."""
        template = self.config['aider']['prompt_template']
        project_config = self.config['projects'][task['project']]
        return template.format(
            title=task['title'],
            description=task['description'],
            project=task['project'],
            project_description=project_config['description'],
            requirements='\n'.join([f"- {k}: {v}" for k, v in task['fields'].items()])
        )

    def execute_aider_command(self, task: Task, prompt: str) -> Optional[str]:
        """Executa o comando do Aider usando a biblioteca aider-chat."""
        try:
            project_config = self.config['projects'][task['project']]
            project_dir = os.path.abspath(project_config['directory'])
            
            # Verifica se o diretório existe
            if not os.path.exists(project_dir):
                print(f"Diretório do projeto não encontrado: {project_dir}")
                return None

            # Verifica se é um diretório git
            if not os.path.exists(os.path.join(project_dir, '.git')):
                print(f"AVISO: O diretório {project_dir} não parece ser um repositório git")
                print("O aider funciona melhor com repositórios git")
                return None

            # Inicializa o repositório git
            repo = Repo(project_dir)
            
            # Faz checkout e pull da branch base
            base_branch = self.config['github']['base_branch']
            print(f"\n=== Atualizando branch base {base_branch} ===")
            try:
                # Faz checkout da branch base
                repo.git.checkout(base_branch)
                # Faz pull da branch base
                repo.git.pull('origin', base_branch)
                print(f"Branch {base_branch} atualizada com sucesso")
            except Exception as e:
                print(f"Erro ao atualizar branch base: {e}")
                return None

            # Configura o ambiente para o Aider
            env = os.environ.copy()
            env['OPENROUTER_API_KEY'] = os.getenv('OPENROUTER_API_KEY')
            
            # Verifica se a chave da API está configurada
            if not env['OPENROUTER_API_KEY']:
                print("AVISO: OPENROUTER_API_KEY não encontrada nas variáveis de ambiente")
                print("Por favor, adicione sua chave da API do OpenRouter no arquivo .env")
                return None

            print("\n=== Iniciando execução do Aider ===")
            print(f"Diretório do projeto: {project_dir}")
            print(f"Modelo: {self.config['openrouter']['model']}")
            print(f"Temperatura: {self.config['openrouter']['temperature']}")
            print(f"API Base: {self.config['openrouter']['base_url']}")
            print(f"API key: {env['OPENROUTER_API_KEY']}")
            print("Prompt:", prompt)
            print("================================\n")

            model = Model(self.config['openrouter']['model'])

            fnames = [project_dir]
            
            io = InputOutput(yes=True, )
            # Create a coder object
            coder = Coder.create(main_model=model, io=io, fnames=fnames)
            # Executa o comando
            response = coder.run(prompt)
            
            print("\n=== Saída do Aider ===")
            print("Resposta:", response)
            print("=====================\n")

            response = coder.run("Sim, crie ou atualize quaisquer arquivos necessários")
            
            print("\n=== Saída do Aider ===")
            print("Resposta:", response)
            print("=====================\n")

            return ftfy.fix_text(response)

        except Exception as e:
            print("\n=== Erro na execução do Aider ===")
            print(f"Tipo do erro: {type(e).__name__}")
            print(f"Mensagem do erro: {str(e)}")
            import traceback
            print("\nTraceback completo:")
            print(traceback.format_exc())
            print("==============================\n")
            return None

    def create_pull_request(self, task: Task, changes: str) -> Optional[str]:
        """Cria um Pull Request no GitHub."""
        try:
          
             # Obtém o repositório específico do projeto
            github_repo = self.get_project_repo(task['project'])

            # Caminho para o repositório local
            repo_path = self.config['projects'][task['project']]['directory']

           
            repo_remote_path = self.config['projects'][task['project']]['repository']
            branch_name = f"feature/{task['key']}"
            pr_title = f"[{task['project']}] {task['key']}: {task['title']}"

            repo = Repo(repo_path)

            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            # Envia a nova branch para o repositório remoto
            github_user = os.getenv('GITHUB_USER')
            github_token = os.getenv('GITHUB_TOKEN')
            origin = repo.remote(name='origin')
            origin.set_url(f'https://{github_user}:{github_token}@github.com/{repo_remote_path}.git')
            origin.push(refspec=f'{branch_name}:{branch_name}')            
          
            
            try:

               # Template do PR
                pr_body = self.config['github']['pr_template'].format(
                    description=task['description'],
                    changes=changes,
                    jira_key=task['key'],
                    project=task['project']
                )

                # Cria o Pull Request
                pr = github_repo.create_pull(
                    title=pr_title,
                    body=ftfy.fix_text(pr_body),
                    head=branch_name,
                    base=self.config['github']['base_branch'],
                    
                )

                pr.add_to_labels("Coded by AI")
                
                print(f"Pull Request criado com sucesso: {pr.html_url}")
                return pr.html_url
                
            except Exception as e:
                print(f"Erro ao executar operação git: {e}")
                if hasattr(e, 'data'):
                    print(f"Detalhes do erro: {e.data}")
                return None
            
        except Exception as e:
            print(f"Erro ao criar Pull Request: {e}")
            if hasattr(e, 'data'):
                print(f"Detalhes do erro: {e.data}")
            return None

    def process_task(self, task_key: str) -> None:
        """Processa uma task do Jira completa."""
        print(f"Processando task {task_key}...")
        
        # Obtém os detalhes da task
        task = self.get_jira_task(task_key)

        # Verifica se o projeto está configurado
        if task['project'] not in self.config['projects']:
            print(f"Projeto {task['project']} não está configurado no config.yaml")
            return
        
        # Gera o prompt para o Aider
        prompt = self.generate_aider_prompt(task)
        
        # Executa o Aider
        changes = self.execute_aider_command(task, prompt)
        if not changes:
            print("Falha ao executar o Aider")
            return
 
        # Cria o Pull Request
        pr_url = self.create_pull_request(task, changes)

        self.comment_jira_task(task_key, f"Pull Request criado: {pr_url}")

    def comment_jira_task(self, task_key: str, comment: str) -> None:
        """Comenta a task no jira"""
        self.jira.add_comment(task_key, comment)


def main() -> None:
    task_to_code = TaskToCode()
    
    # Exemplo de uso
    task_key = input("Digite a chave da task do Jira (ex: PROJ-123): ")
    task_to_code.process_task(task_key)


if __name__ == "__main__":
    main() 