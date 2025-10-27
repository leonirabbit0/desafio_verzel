import json
from dotenv import load_dotenv
import os
from openai import OpenAI
from services.google_service import GoogleCalendar
from database.firebase import db

import datetime

load_dotenv() 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VERZEL_ASSISTANT = os.getenv("VERZEL_ASSISTANT")

PROMPT = """Você é Roberto, um assistente virtual empático e cordial da empresa Verzel, especializada em soluções tecnológicas. 
Seu papel é atuar como um SDR automatizado (pré-vendas), conduzindo conversas naturais com leads interessados em conhecer ou contratar os serviços da Verzel.

No início do contato, seja cordial. No decorrer da conversa, pergunte o nome do cliente e entenda o propósito do contato — 
se ele deseja apenas saber mais sobre a empresa ou se tem interesse em agendar uma reunião. 
NUNCA PERGUNTE TUDO DE UMA VEZ. Conduza o diálogo de forma natural e envolvente, mantendo um tom leve, profissional e simpático. 
Evite mensagens longas.

Quando o cliente demonstrar explicitamente interesse em contratar os serviços da Verzel ou marcar uma reunião,
chame a função "verificar_interesse_cliente" com "confirmacao_interesse" definido como true.

Caso o cliente ainda esteja apenas conversando ou explorando, chame a função
"verificar_interesse_cliente" com "confirmacao_interesse" definido como false.

Seu objetivo é coletar informações básicas em etapas:
1. Pergunte o nome ou como o cliente prefere ser chamado(a);
2. Pergunte sobre as necessidades do cliente e veja se elas se encaixam no perfil da empresa;
3. Se identificar interesse, pergunte de onde o cliente fala;
4. Peça o email apenas quando o cliente confirmar o interesse em marcar uma reunião.

Se o cliente quiser agendar, ofereça horários disponíveis, confirme o melhor horário e realize o agendamento automaticamente 
via API de agenda (Calendly, Cal.com ou similar). Após o agendamento, confirme a reunião e registre as informações coletadas.  
Todos os leads, mesmo os que não marcarem reunião, devem ser registrados no Pipefy, criando ou atualizando um card com os dados obtidos.

Mantenha o contexto da conversa até o encerramento do atendimento, garantindo uma experiência agradável e personalizada.  
Utilize linguagem clara, empática e próxima, sem soar robótico. Se o cliente quiser encerrar, agradeça e finalize de forma cordial.Você é Roberto, um assistente virtual empático e cordial da empresa Verzel, especializada em soluções tecnológicas. 
Seu papel é atuar como um SDR automatizado (pré-vendas), conduzindo conversas naturais com leads interessados em conhecer ou contratar os serviços da Verzel.
"""

FUNCTION = {
    "type": "function",
    "name": "verificar_interesse_cliente",
    "description": (
        "Analisa a última mensagem do cliente e determina se ele confirmou "
        "explicitamente interesse em marcar uma reunião ou contratar os serviços da Verzel."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "confirmacao_interesse": {
                "type": "boolean",
                "description": "True se o cliente demonstrar interesse em marcar reunião ou contratar a Verzel."
            }
        },
        "required": ["confirmacao_interesse"]
    }
}


RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "assistant_response",
        "schema": {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": [
                        "none",
                        "ask_name",
                        "ask_need",
                        "ask_location",
                        "offer_meeting",
                        "schedule_meeting",
                        "register_lead"
                    ]
                },
                "data": {"type": "object"}
            },
            "required": ["reply", "action"]
        }
    }
}


class FirebaseOrganizer():
    
    def check_user(user_id:str):
        doc_ref = db.collection("conversation").document(user_id)
        
        if not doc_ref.get().exists:
            return False
        else:
            return True
        
    def get_conversation(self, user_id:str):
        doc_ref = db.collection("conversations").document(user_id)
        
        doc = doc_ref.get()
        
        if not doc.exists:
            print("Não existe.")
            return []
        
        messages_ref = doc_ref.collection("messages").order_by("dateTime", direction="ASCENDING")
        
        messages = messages_ref.get()
        
        messages_list = []
        for message in messages:
            messages_list.append({"role": message.get("role"), "content": message.get("content")})
            
        return messages_list

    def update_conversation(self, user_id, context:list):
        doc_ref = db.collection("conversations").document(user_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            doc_ref.set({"user_id": user_id, "created_at": datetime.datetime.now()})
        
        for item in context:
            doc_ref.collection("messages").add(item)
        
    
class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._assistant = self.get_openai_assistant()
        self.Firebase = FirebaseOrganizer()
        self.Google = GoogleCalendar()
    
    def get_tools(self):
        return self._assistant.tools
    
    def handle_assistant_functions(self, function_name: str, user_id: str) -> str:
        """
        Executa funções de negócio e retorna uma nova mensagem textual para o modelo continuar a conversa.
        """
        if function_name == "verificar_interesse_cliente":
            horarios = self.Google.get_available(datetime.datetime.now(), datetime.datetime.now() + datetime.timedelta(days=30))
            if not horarios:
                return "Infelizmente, não encontrei horários disponíveis no momento. Quer tentar novamente mais tarde?"

            msg = "Perfeito! Vejo que você tem interesse em conversar com a Verzel.\n"
            msg += "Temos os seguintes horários disponíveis:\n"
            for h in horarios[:5]:  # mostra até 5 opções
                msg += f"- Das {h.get('start')} às {h.get('end')}\n"

            msg += "Qual desses horários funciona melhor pra você?"
            
            print(msg)
            return msg

        return None
            
    
    def send_message(self, user_id: str, message_received:dict, recursion_depth: int = 0) -> str:
        context = self.Firebase.get_conversation(user_id)
        context += [{"role": "user", "content": message_received.get("content", "")}]
        
        response = self.client.responses.create(
            model="gpt-4o-mini",
            instructions=PROMPT,
            input=context,
            tools=[FUNCTION]
        )

        for item in response.output:
            if item.type == "message":
                context_to_update = [
                    message_received,
                    {"role": response.output[0].role, "content": response.output[0].content[0].text, "dateTime": datetime.datetime.now()},
                ]
            
            elif item.type == "function_call":
                print(f"Chamou função: {item.name}")
                # Chama a função de negócio
                new_message = self.handle_assistant_functions(item.name, user_id)
                if new_message:
                    # Chama novamente a si mesmo — recursão controlada
                    return self.send_message(
                        user_id,
                        {"role": "assistant", "content": new_message, "dateTime": datetime.datetime.now()},
                        recursion_depth + 1
                    )
        
        
        self.Firebase.update_conversation(user_id, context_to_update)
        return response.output[0].content
    
    def get_openai_assistant(self):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            assistant = client.beta.assistants.retrieve(assistant_id=VERZEL_ASSISTANT)
            return assistant
        except:
            pass

        
    @classmethod
    def update_prevenda():
        return True


