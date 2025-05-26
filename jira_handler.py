import os
from datetime import datetime
from typing import Dict, List, Optional

import ftfy
from dateutil import parser
from jira import JIRA

from type_definitions import Task


class JiraHandler:
    def __init__(self, jira_url: str, jira_email: str, jira_token: str) -> None:
        self.jira = JIRA(
            server=jira_url,
            basic_auth=(jira_email, jira_token)
        )

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

    def get_task(self, task_key: str) -> Task:
        """Obtém os detalhes de uma task do Jira."""
        issue = self.jira.issue(task_key)
        
        # Extrai os campos da descrição e corrige a codificação
        description = issue.fields.description
        if isinstance(description, bytes):
            description = description.decode('utf-8')
        description = ftfy.fix_text(description)
        
        fields = self.parse_description_fields(description)
        
        # Converte a data de atualização para datetime
        updated = parser.parse(issue.fields.updated)
        
        return {
            'key': issue.key,
            'title': ftfy.fix_text(issue.fields.summary),
            'description': description,
            'type': fields.get('Tipo', ''),
            'project': fields.get('Projeto', ''),
            'fields': fields,
            'updated': updated
        }

    def comment_task(self, task_key: str, comment: str) -> None:
        """Comenta a task no jira"""
        self.jira.add_comment(task_key, comment)

    def get_correction_comments(self, task_key: str, since: Optional[datetime] = None) -> List[Dict]:
        """Obtém os comentários de correção desde uma data específica."""
        issue = self.jira.issue(task_key)
        comments = []
        
        for comment in issue.fields.comment.comments:
            # Converte a data do comentário para datetime
            comment_updated = parser.parse(comment.updated).replace(tzinfo=None)
            
            # Se não houver data de referência ou o comentário for mais recente
            if not since or comment_updated > since:
                # Verifica se é um comentário de correção (começa com [CORREÇÃO])
                if comment.body.startswith('[CORREÇÃO]'):
                    comments.append({
                        'author': comment.author.displayName,
                        'body': comment.body.replace('[CORREÇÃO]', '').strip(),
                        'updated': comment_updated
                    })
        
        return comments

    def has_description_changed(self, task_key: str, last_updated: datetime) -> bool:
        """Verifica se a descrição da task foi alterada desde a última atualização."""
        issue = self.jira.issue(task_key)
        # Converte a data de atualização para datetime
        issue_updated = parser.parse(issue.fields.updated).replace(tzinfo=None)
        return issue_updated > last_updated

    def get_task_updates(self, task_key: str, last_updated: datetime) -> Optional[Task]:
        """Obtém as atualizações da task se houver mudanças na descrição."""
        if self.has_description_changed(task_key, last_updated):
            return self.get_task(task_key)
        return None 