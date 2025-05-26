import os
from typing import Any, Dict, List, Optional

import ftfy
from git import Repo
from github import Github

from type_definitions import Task


class GitHubHandler:
    def __init__(self, github_token: str, github_user: str) -> None:
        self.github = Github(github_token)
        self.github_user = github_user
        self.github_token = github_token

    def get_project_repo(self, project: str, config: dict) -> Any:
        """Obtém o repositório do GitHub para um projeto específico."""
        project_config = config['projects'][project]
        return self.github.get_repo(project_config['repository'])

    def create_pull_request(self, task: Task, changes: str, config: dict) -> Optional[str]:
        """Cria um Pull Request no GitHub."""
        try:
            # Obtém o repositório específico do projeto
            github_repo = self.get_project_repo(task['project'], config)

            # Caminho para o repositório local
            repo_path = config['projects'][task['project']]['directory']
            repo_remote_path = config['projects'][task['project']]['repository']
            branch_name = f"feature/{task['key']}"
            pr_title = f"[{task['project']}] {task['key']}: {task['title']}"

            repo = Repo(repo_path)

            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            # Envia a nova branch para o repositório remoto
            origin = repo.remote(name='origin')
            origin.set_url(f'https://{self.github_user}:{self.github_token}@github.com/{repo_remote_path}.git')
            origin.push(refspec=f'{branch_name}:{branch_name}')            
          
            try:
                # Template do PR
                pr_body = config['github']['pr_template'].format(
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
                    base=config['github']['base_branch'],
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

    def checkout_and_pull_base(self, project_dir: str, base_branch: str) -> bool:
        """Faz checkout e pull da branch base."""
        try:
            repo = Repo(project_dir)
            repo.git.checkout(base_branch)
            repo.git.pull('origin', base_branch)
            return True
        except Exception as e:
            print(f"Erro ao atualizar branch base: {e}")
            return False

    def update_existing_branch(self, task: Task, changes: str, config: dict) -> Optional[str]:
        """Atualiza uma branch existente com as correções."""
        try:
            repo_path = config['projects'][task['project']]['directory']
            branch_name = f"feature/{task['key']}"
            
            repo = Repo(repo_path)
            
            # Verifica se a branch existe
            if branch_name not in [ref.name for ref in repo.references]:
                print(f"Branch {branch_name} não encontrada")
                return None
            
            # Faz checkout da branch
            repo.git.checkout(branch_name)
            
            # Adiciona todas as alterações
            repo.git.add(A=True)
            
            # Cria um commit com as correções
            commit_message = f"fix: Aplicando correções para {task['key']} {changes}"
            repo.index.commit(commit_message)
            
            # Faz push das alterações
            origin = repo.remote(name='origin')
            origin.push(branch_name)
            
            # Obtém o PR existente
            github_repo = self.get_project_repo(task['project'], config)
            prs = github_repo.get_pulls(state='open', head=branch_name)
            
            # Atualiza o PR com as novas alterações
            for pr in prs:
                pr.create_issue_comment(f"✨ Novas correções aplicadas:\n\n{changes}")
                return pr.html_url
            
            return None
            
        except Exception as e:
            print(f"Erro ao atualizar branch: {e}")
            return None

    def apply_corrections(self, task: Task, corrections: List[Dict], config: dict) -> bool:
        """Aplica correções via comentários na branch existente."""
        try:
            repo_path = config['projects'][task['project']]['directory']
            branch_name = f"feature/{task['key']}"
            
            repo = Repo(repo_path)
            
            # Verifica se a branch existe
            if branch_name not in [ref.name for ref in repo.references]:
                print(f"Branch {branch_name} não encontrada")
                return False
            
            # Faz checkout da branch
            repo.git.checkout(branch_name)
            
            # Aplica cada correção
            for correction in corrections:
                print(f"\n=== Aplicando correção de {correction['author']} ===")
                print(f"Correção: {correction['body']}")
                
                # Aqui você pode implementar a lógica para aplicar as correções
                # Por exemplo, usando o Aider para aplicar as mudanças
                
            return True
            
        except Exception as e:
            print(f"Erro ao aplicar correções: {e}")
            return False

    def reset_branch(self, task: Task, config: dict) -> bool:
        """Reseta a branch para o estado da branch base."""
        try:
            repo_path = config['projects'][task['project']]['directory']
            branch_name = f"feature/{task['key']}"
            base_branch = config['github']['base_branch']
            
            repo = Repo(repo_path)
            
            # Verifica se a branch existe
            if branch_name not in [ref.name for ref in repo.references]:
                print(f"Branch {branch_name} não encontrada")
                return False
            
            # Faz checkout da branch base
            repo.git.checkout(base_branch)
            repo.git.pull('origin', base_branch)
            
            # Deleta a branch local
            repo.delete_head(branch_name, force=True)
            
            # Deleta a branch remota
            origin = repo.remote(name='origin')
            origin.push(f':{branch_name}')
            
            return True
            
        except Exception as e:
            print(f"Erro ao resetar branch: {e}")
            return False 