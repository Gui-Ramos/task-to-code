import os
from typing import Dict, List, Optional

import ftfy
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model

from type_definitions import Task


class AiderHandler:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.model = Model(config['openrouter']['model'])

    def generate_prompt(self, task: Task) -> str:
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

    def generate_correction_prompt(self, task: Task, corrections: List[Dict]) -> str:
        """Gera um prompt para aplicar correções específicas."""
        correction_text = "\n".join([
            f"Correção de {correction['author']}:\n{correction['body']}"
            for correction in corrections
        ])
        
        return f"""
        Analise as seguintes correções para a task {task['key']} e aplique-as no código:
        
        {correction_text}
        
        Por favor, aplique estas correções mantendo a consistência do código.
        """

    def execute_command(self, task: Task, prompt: str) -> Optional[str]:
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

            fnames = [project_dir]
            
            io = InputOutput(yes=True)
            # Create a coder object
            coder = Coder.create(main_model=self.model, io=io, fnames=fnames)
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

    def apply_corrections(self, task: Task, corrections: List[Dict]) -> Optional[str]:
        """Aplica correções específicas usando o Aider."""
        prompt = self.generate_correction_prompt(task, corrections)
        return self.execute_command(task, prompt) 