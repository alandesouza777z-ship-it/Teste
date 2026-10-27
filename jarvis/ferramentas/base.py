"""Utilitário para declarar ferramentas no formato da API da Anthropic."""


def _schema(nome, descricao, propriedades=None, obrigatorios=None):
    return {
        "name": nome,
        "description": descricao,
        "input_schema": {
            "type": "object",
            "properties": propriedades or {},
            "required": obrigatorios or [],
        },
    }
