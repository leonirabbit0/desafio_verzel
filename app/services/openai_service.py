import json
from dotenv import load_dotenv
import os
from openai import OpenAI
from app.services.google_service import GoogleCalendar
from app.services.pipefy_service import PipefyService
from app.database.firebase import db

import datetime
import re
import traceback

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VERZEL_ASSISTANT = os.getenv("VERZEL_ASSISTANT")

PROMPT = """
Você é Roberto, assistente virtual da Verzel, especializado em marcar reuniões.
Siga O FLUXO estritamente: pedir nome → entender necessidade (dor) → confirmar interesse → oferecer horários → coletar email → agendar.
Responda de forma curta (1-3 frases) e nunca pergunte múltiplas coisas ao mesmo tempo.
"""

# --- Tool schemas (mantidos) ---
CONFIRMAR_NOME = {
    "type": "function",
    "name": "confirmar_nome",
    "description": "Salva o nome do cliente quando ele informar como quer ser chamado.",
    "parameters": {
        "type": "object",
        "properties": {
            "nome": {"type": "string"}
        },
        "required": ["nome"]
    }
}

CONFIRMAR_DOR = {
    "type": "function",
    "name": "confirmar_dor",
    "description": "Salva o problema/necessidade/dor que o cliente quer resolver.",
    "parameters": {
        "type": "object",
        "properties": {
            "dor": {"type": "string"}
        },
        "required": ["dor"]
    }
}

CONFIRMAR_INTERESSE = {
    "type": "function",
    "name": "confirmar_interesse",
    "description": "Chamada quando o cliente confirma que quer marcar reunião.",
    "parameters": {
        "type": "object",
        "properties": {
            "confirmado": {"type": "boolean"}
        },
        "required": ["confirmado"]
    }
}

CONFIRMAR_HORARIO = {
    "type": "function",
    "name": "confirmar_horario",
    "description": "Escolha do horário pelo cliente. Aceita 'horario_iso' (ISO) ou 'choice' (índice 1-based).",
    "parameters": {
        "type": "object",
        "properties": {
            "horario_iso": {"type": "string"},
            "choice": {"type": "integer"}
        },
        "required": []
    }
}

CONFIRMAR_EMAIL = {
    "type": "function",
    "name": "confirmar_email",
    "description": "Salva o email do cliente.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string"}
        },
        "required": ["email"]
    }
}

class FirebaseOrganizer():
    def get_conversation(self, user_id: str):
        doc_ref = db.collection("conversations").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            return []
        messages_ref = doc_ref.collection("messages").order_by("dateTime")
        messages = messages_ref.stream()
        messages_list = []
        for message in messages:
            msg_data = message.to_dict()
            messages_list.append({"role": msg_data.get("role"), "content": msg_data.get("content")})
        return messages_list

    def update_conversation(self, user_id, context: list):
        doc_ref = db.collection("conversations").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            doc_ref.set({"user_id": user_id, "created_at": datetime.datetime.utcnow(), "status": "in_progress"})
        for item in context:
            item_copy = dict(item)
            item_copy["dateTime"] = datetime.datetime.utcnow()
            doc_ref.collection("messages").add(item_copy)

    def salvar_campo(self, user_id, campo, valor):
        doc_ref = db.collection("conversations").document(user_id)
        doc_ref.set({campo: valor}, merge=True)
        print(f"salvou {campo}: {valor}")

    def get_dados_cliente(self, user_id):
        doc_ref = db.collection("conversations").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            return {}
        return doc.to_dict()

    def dados_completos(self, user_id):
        dados = self.get_dados_cliente(user_id)
        campos_obrigatorios = ['nome', 'dor', 'interesse_confirmado', 'horario_escolhido', 'email']
        faltando = [c for c in campos_obrigatorios if not dados.get(c)]
        if faltando:
            return faltando
        return []

    def get_etapa(self, user_id):
        doc_ref = db.collection("conversations").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            # inicializa documento com etapa
            doc_ref.set({"user_id": user_id, "created_at": datetime.datetime.utcnow(), "etapa_atual": "perguntar_nome"}, merge=True)
            return "perguntar_nome"
        dados = doc.to_dict()
        return dados.get("etapa_atual", "perguntar_nome")

    def set_etapa(self, user_id, etapa):
        self.salvar_campo(user_id, "etapa_atual", etapa)

    def avancar_etapa(self, user_id):
        ordem = ["perguntar_nome", "perguntar_dor", "confirmar_interesse", "escolher_horario", "coletar_email", "finalizado"]
        atual = self.get_etapa(user_id)
        try:
            proxima = ordem[ordem.index(atual) + 1]
        except (ValueError, IndexError):
            proxima = "finalizado"
        self.set_etapa(user_id, proxima)
        print(f"➡️ Avançou etapa: {proxima}")
        return proxima
    
    def get_messages(self, session_id: str):
        """Busca todas as mensagens de uma sessão para exibir no frontend"""
        try:
            messages_ref = (
                db.collection('conversations')
                .document(session_id)
                .collection('messages')
                .order_by('dateTime')
            )
            
            docs = messages_ref.stream()
            
            messages = []
            for doc in docs:
                data = doc.to_dict()
                messages.append({
                    "role": data.get("role"),
                    "content": data.get("content")
                })
            
            print(f"{len(messages)} mensagens carregadas para {session_id}")
            return messages
            
        except Exception as e:
            print(f"Erro ao buscar mensagens: {e}")
            traceback.print_exc()
            return []


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._assistant = self.get_openai_assistant()
        self.Firebase = FirebaseOrganizer()
        self.Google = GoogleCalendar()
        self.Pipefy = PipefyService()
        self.db = db

    def get_tools(self):
        return self._assistant.tools if self._assistant else []

    def _validate_email(self, email: str) -> bool:
        # regex simples, suficiente para validar formato básico
        if not isinstance(email, str): return False
        pattern = r"^[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+$"
        return re.match(pattern, email) is not None

    def _parse_iso_safe(self, iso_str: str):
        try:
            return datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _format_slots_message(self, slots):
        # slots expected list of dicts with keys 'start', 'end' as datetimes
        lines = []
        for i, s in enumerate(slots, start=1):
            local_time = s["start"].astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
            lines.append(f"{i}. {local_time.strftime('%A, %d/%m às %H:%M')}")
        return "Ótimo! Tenho estes horários disponíveis:\n\n" + "\n".join(lines) + "\n\nResponda com o número (ex: 1) para escolher."

    def handle_assistant_functions(self, function_name: str, user_id: str, args: dict) -> dict:
        """
        Retorna:
          - should_continue: se deve gerar a próxima pergunta imediatamente
          - message: mensagem direta para o usuário (quando aplicável)
        """
        try:
            if function_name == "confirmar_nome":
                nome = args.get("nome", "").strip()
                if not nome:
                    return {"should_continue": False, "message": "Não entendi o nome. Pode repetir?"}
                # opcional: limpar caracteres inválidos
                self.Firebase.salvar_campo(user_id, "nome", nome)
                self.Firebase.avancar_etapa(user_id)
                return {"should_continue": True, "message": None}

            elif function_name == "confirmar_dor":
                dor = args.get("dor", "").strip()
                if not dor:
                    return {"should_continue": False, "message": "Pode descrever rapidamente o que você precisa?"}
                self.Firebase.salvar_campo(user_id, "dor", dor)
                self.Firebase.avancar_etapa(user_id)
                return {"should_continue": True, "message": None}

            elif function_name == "confirmar_interesse":
                confirmado = args.get("confirmado", False)
                if not isinstance(confirmado, bool):
                    return {"should_continue": False, "message": "Preciso de uma confirmação (sim/não)."}
                if not confirmado:
                    # usuário não quer reunião
                    self.Firebase.salvar_campo(user_id, "interesse_confirmado", False)
                    self.Firebase.set_etapa(user_id, "finalizado")
                    return {"should_continue": False, "message": "Entendi. Se mudar de ideia, me avise!"}
                # confirmado == True
                self.Firebase.salvar_campo(user_id, "interesse_confirmado", True)
                # pega horários e salva slots_oferecidos no documento
                horarios = self.Google.get_available_slots(days_ahead=7)
                if not horarios:
                    return {"should_continue": False, "message": "Desculpe — no momento não há horários disponíveis. Posso tentar novamente mais tarde?"}
                # transforma para serializável e salva
                slots_list = []
                for s in horarios[:5]:
                    # certifica que start/end são datetimes
                    start_iso = s["start"].isoformat()
                    end_iso = s["end"].isoformat()
                    slots_list.append({"start": start_iso, "end": end_iso})
                self.Firebase.salvar_campo(user_id, "slots_oferecidos", json.dumps(slots_list))
                self.Firebase.avancar_etapa(user_id)
                # Formata mensagem com os horários no timezone -3
                # reconstrói os datetimes para mensagem legível
                parsed_slots = []
                for s in slots_list:
                    parsed_slots.append({"start": datetime.datetime.fromisoformat(s["start"])})
                msg = self._format_slots_message(parsed_slots)
                return {"should_continue": False, "message": msg}

            elif function_name == "confirmar_horario":
                # aceitar 'choice' (1-based) ou 'horario_iso'
                choice = args.get("choice")
                horario_iso = args.get("horario_iso")
                dados = self.Firebase.get_dados_cliente(user_id)
                slots_json = dados.get("slots_oferecidos")
                if not slots_json:
                    return {"should_continue": False, "message": "Não localizei os horários que ofereci. Pode confirmar interesse novamente?"}
                slots = json.loads(slots_json)
                # escolha por índice
                if choice:
                    try:
                        idx = int(choice) - 1
                        if idx < 0 or idx >= len(slots):
                            raise IndexError()
                        selected_iso = slots[idx]["start"]
                        self.Firebase.salvar_campo(user_id, "horario_escolhido", selected_iso)
                        self.Firebase.avancar_etapa(user_id)
                        return {"should_continue": True, "message": None}
                    except Exception:
                        return {"should_continue": False, "message": "Escolha inválida. Responda com o número do horário (ex: 1)."}
                # escolha por ISO
                if horario_iso:
                    parsed = self._parse_iso_safe(horario_iso)
                    if not parsed:
                        return {"should_continue": False, "message": "Não consegui entender a data/hora. Use o formato ISO ou escolha o número do slot."}
                    # validar se esse ISO está entre slots oferecidos (segurança)
                    iso_matches = [s for s in slots if s["start"].startswith(horario_iso[:19])]
                    if not iso_matches:
                        # ainda podemos aceitar, mas aviso
                        self.Firebase.salvar_campo(user_id, "horario_escolhido", horario_iso)
                        self.Firebase.avancar_etapa(user_id)
                        return {"should_continue": True, "message": None}
                    self.Firebase.salvar_campo(user_id, "horario_escolhido", horario_iso)
                    self.Firebase.avancar_etapa(user_id)
                    return {"should_continue": True, "message": None}
                return {"should_continue": False, "message": "Por favor, escolha um dos horários respondendo com o número (ex: 1) ou envie o horário em ISO."}

            elif function_name == "confirmar_email":
                email = args.get("email", "").strip()
                if not self._validate_email(email):
                    return {"should_continue": False, "message": "Esse email não parece válido. Pode verificar e enviar novamente?"}
                self.Firebase.salvar_campo(user_id, "email", email)
                self.Firebase.avancar_etapa(user_id)
                return {"should_continue": True, "message": None}

        except Exception as e:
            print("❌ Erro em handle_assistant_functions:", e)
            traceback.print_exc()
            return {"should_continue": False, "message": "Ocorreu um erro interno. Pode tentar novamente?"}

        return {"should_continue": False, "message": None}

    def send_message(self, user_id: str, message_received: dict) -> str:
        """
        Fluxo principal: processa a mensagem do usuário e gera a resposta.
        """
        # garante que o documento existe e salva imediatamente a mensagem do usuário
        self.Firebase.update_conversation(user_id, [message_received])

        #  se todos os dados já foram coletados
        faltando = self.Firebase.dados_completos(user_id)
        if not faltando:
            return self.marcar_reuniao(user_id)

        etapa = self.Firebase.get_etapa(user_id)
        prompt = f"{PROMPT}\nEtapa atual: {etapa}\nCampos faltando: {', '.join(faltando)}"

        #prepara contexto
        context = self.Firebase.get_conversation(user_id)

        #define apenas a tool correspondente à etapa
        tools_ = []
        if etapa == "perguntar_nome":
            tools_ = [CONFIRMAR_NOME]
        elif etapa == "perguntar_dor":
            tools_ = [CONFIRMAR_DOR]
        elif etapa == "confirmar_interesse":
            tools_ = [CONFIRMAR_INTERESSE]
        elif etapa == "escolher_horario":
            tools_ = [CONFIRMAR_HORARIO]
        elif etapa == "coletar_email":
            tools_ = [CONFIRMAR_EMAIL]

        print(f"Tools liberadas: {[t['name'] for t in tools_]}, etapa={etapa}")

        # chama a API 
        response = self.client.responses.create(
            model="gpt-4o-mini",
            instructions=prompt,
            input=context,
            tools=tools_
        )

        assistant_message = ""
        function_response_direct = None
        should_repeat = False

        # percorre saída e trata mensagens ou chamadas de função
        for item in response.output:
            if item.type == "message":
                # mensagem textual do assistant
                assistant_message = item.content[0].text
            elif item.type == "function_call":
                args = json.loads(item.arguments)
                print(f"🔄 Model solicitou função: {item.name} args={args}")
                function_result = self.handle_assistant_functions(item.name, user_id, args)
                # se a função retornou uma mensagem direta, usá-la
                if function_result.get("message"):
                    function_response_direct = function_result["message"]
                # se a função diz para continuar 
                # gera a próxima saída 
                should_repeat = function_result.get("should_continue", False)

        if function_response_direct:
            assistant_message = function_response_direct

        # se a função alterou estado e deve continuar, chama send_message recursivamente
        if should_repeat:
            # chama recursivamente
            return self.send_message(user_id, {"role": "user", "content": ""})

        # salva resposta do assistant no histórico
        context_to_save = [{"role": "assistant", "content": assistant_message}]
        self.Firebase.update_conversation(user_id, context_to_save)

        # se todos os dados estão ok, dispara agendamento
        faltando_depois = self.Firebase.dados_completos(user_id)
        if not faltando_depois:
            return self.marcar_reuniao(user_id)

        return assistant_message

    def get_openai_assistant(self):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            assistant = client.beta.assistants.retrieve(assistant_id=VERZEL_ASSISTANT)
            return assistant
        except Exception:
            return None

    def marcar_reuniao(self, user_id):
        dados = self.Firebase.get_dados_cliente(user_id)
        nome = dados.get("nome", "Cliente")
        email = dados.get("email", "")
        horario_iso = dados.get("horario_escolhido")
        dor = dados.get("dor", "Sem descrição")
        try:
            inicio = datetime.datetime.fromisoformat(horario_iso.replace("Z", "+00:00"))
            fim = inicio + datetime.timedelta(hours=1)
            event = self.Google.create_event(
                summary=f"Reunião Verzel - {nome}",
                inicio=inicio,
                fim=fim,
                description=f"Cliente: {nome}\nEmail: {email}\n\nNecessidade:\n{dor}"
            )
            event_link = event.get('htmlLink', '')
            resultado_pipefy = self.Pipefy.criar_card(dados, event_link)
            self.Firebase.salvar_campo(user_id, "status", "agendado")
            self.Firebase.salvar_campo(user_id, "event_link", event_link)
            self.Firebase.salvar_campo(user_id, "pipefy_card_id", resultado_pipefy.get('card_id', ''))
            self.Firebase.salvar_campo(user_id, "pipefy_card_url", resultado_pipefy.get('card_url', ''))
            local_time = inicio.astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
            return (
                f"🎉 Tudo certo, {nome}!\n"
                f"Sua reunião está marcada para {local_time.strftime('%d/%m às %H:%M')}h.\n"
                f"Enviei um convite para {email}.\n\nLink: {event_link}"
            )
        except Exception as e:
            print("Erro ao criar evento:", e)
            traceback.print_exc()
            return "Ops! Tive um problema ao agendar. Pode tentar novamente?"
