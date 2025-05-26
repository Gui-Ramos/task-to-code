import os
from datetime import datetime
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from aider_handler import AiderHandler
from github_handler import GitHubHandler
from jira_handler import JiraHandler
from type_definitions import Config, Task


class TaskToCode:
    def __init__(self) -> None:
        load_dotenv()
        self.config: Config = self.load_config()
        
        # Inicializa os handlers
        self.jira_handler = JiraHandler(
            jira_url=os.getenv('JIRA_URL'),
            jira_email=os.getenv('JIRA_EMAIL'),
            jira_token=os.getenv('JIRA_API_TOKEN')
        )
        
        self.github_handler = GitHubHandler(
            github_token=os.getenv('GITHUB_TOKEN'),
            github_user=os.getenv('GITHUB_USER')
        )
        
        self.aider_handler = AiderHandler(self.config)

    def load_config(self) -> Config:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def process_task(self, task_key: str) -> None:
        """Processa uma task do Jira completa."""
        print(f"Processando task {task_key}...")
        
        # Obtém os detalhes da task
        task = self.jira_handler.get_task(task_key)

        # Verifica se o projeto está configurado
        if task['project'] not in self.config['projects']:
            print(f"Projeto {task['project']} não está configurado no config.yaml")
            return
        
        # Gera o prompt para o Aider
        prompt = self.aider_handler.generate_prompt(task)
        
        # Executa o Aider
        changes = self.aider_handler.execute_command(task, prompt)
        if not changes:
            print("Falha ao executar o Aider")
            return
 
        # Cria o Pull Request
        pr_url = self.github_handler.create_pull_request(task, changes, self.config)
        if pr_url:
            self.jira_handler.comment_task(task_key, f"🎉 PR criado com sucesso!\n\n🔗 Link: {pr_url}\n\n🤖 Código gerado automaticamente com IA\n\n💡 Dica: Revise as alterações e aproveite o tempo economizado!")

    def process_corrections(self, task_key: str, last_updated: datetime) -> None:
        """Processa correções para uma task existente."""
        print(f"Verificando correções para task {task_key}...")
        
        # Verifica se houve atualização na descrição da task
        updated_task = self.jira_handler.get_task_updates(task_key, last_updated)

        # Verifica se há comentários de correção
        corrections = self.jira_handler.get_correction_comments(task_key, last_updated)
        if corrections:
            print(f"🔧 Encontradas {len(corrections)} correções para aplicar...")
            
            # Aplica as correções
            changes = self.aider_handler.apply_corrections(updated_task or self.jira_handler.get_task(task_key), corrections)
            if changes:
                # Atualiza a branch existente com as correções
                pr_url = self.github_handler.update_existing_branch(
                    updated_task or self.jira_handler.get_task(task_key),
                    changes,
                    self.config
                )
                if pr_url:
                    self.jira_handler.comment_task(task_key, f"✨ Correções aplicadas com sucesso!\n\n🔗 Link do PR atualizado: {pr_url}")
                return

        
        if updated_task:
            print("📝 Descrição da task foi atualizada. Recriando implementação...")
            
            # Reseta a branch
            if self.github_handler.reset_branch(updated_task, self.config):
                # Processa a task novamente com a nova descrição
                self.process_task(task_key)
            return   

def main() -> None:
    task_to_code = TaskToCode()
    
    # Exemplo de uso
    task_key = input("Digite a chave da task do Jira (ex: PROJ-123): ")
    
    # Processa a task inicialmente
    # task_to_code.process_task(task_key)
    
    # Aguarda por correções
    last_updated = datetime.now()
    while True:
        try:
            input("\nPressione Enter para verificar correções (ou Ctrl+C para sair)...")
            task_to_code.process_corrections(task_key, last_updated)
            last_updated = datetime.now()
        except KeyboardInterrupt:
            print("\nEncerrando...")
            break


if __name__ == "__main__":
    main() 