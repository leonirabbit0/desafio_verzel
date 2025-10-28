import os
import requests
import datetime
from dotenv import load_dotenv

load_dotenv()

class PipefyService:
    def __init__(self):
        self.token = os.getenv("PIPEFY_API_KEY")
        self.pipe_id = os.getenv("PIPEFY_PIPE_ID")
        self.phase_id = os.getenv("PIPEFY_PHASE_ID", "340736206")  # Fase "Marcado"
        self.url = "https://api.pipefy.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def listar_campos(self):
        """Lista todos os campos do pipe para descobrir os IDs"""
        query = """
        {
          pipe(id: %s) {
            phases {
              id
              name
              fields {
                id
                label
                type
              }
            }
          }
        }
        """ % self.pipe_id
        
        response = requests.post(
            self.url,
            json={"query": query},
            headers=self.headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("📋 Campos disponíveis no Pipe:\n")
            for phase in result['data']['pipe']['phases']:
                print(f"\n🔹 Fase: {phase['name']} (ID: {phase['id']})")
                if phase['fields']:
                    for field in phase['fields']:
                        print(f"   • {field['label']}: {field['id']} (tipo: {field['type']})")
                else:
                    print("⚠️ Nenhum campo cadastrado nesta fase")
            return result
        else:
            print(f"Erro ao listar campos: {response.status_code}")
            return None
    
    def criar_card(self, dados_cliente: dict, event_link: str = None) -> dict:
        """
        Cria um card no Pipefy com os dados do cliente.
        
        Args:
            dados_cliente: dict com keys: nome, email, dor, horario_escolhido
            event_link: link do evento do Google Calendar
            
        Returns:
            dict com 'success' (bool) e 'card_id' (str) ou 'error' (str)
        """
        try:
            if not self.token or not self.pipe_id:
                return {
                    "success": False,
                    "error": "Credenciais do Pipefy não configuradas"
                }
            
            # Pega os dados
            nome = dados_cliente.get("nome", "Cliente")
            email = dados_cliente.get("email", "")
            dor = dados_cliente.get("dor", "Não informado")
            horario_iso = dados_cliente.get("horario_escolhido", "")
            
            # Formata a data da reunião
            data_reuniao_formatada = ""
            if horario_iso:
                try:
                    dt = datetime.datetime.fromisoformat(horario_iso.replace("Z", "+00:00"))
                    # Converte para horário de Brasília (UTC-3)
                    local_time = dt.astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
                    data_reuniao_formatada = local_time.strftime("%d/%m/%Y %H:%M")
                except Exception as e:
                    print(f"Erro ao formatar data: {e}")
            
            # Monta o título do card
            titulo = f"Reunião - {nome}"
            
            mutation = """
            mutation {
              createCard(input: {
                pipe_id: "%s"
                phase_id: "%s"
                title: "%s"
              }) {
                card {
                  id
                  title
                  url
                }
              }
            }
            """ % (
                self.pipe_id,
                self.phase_id,
                titulo
            )
            
            """
            mutation = '''
            mutation {
              createCard(input: {
                pipe_id: "%s"
                phase_id: "%s"
                title: "%s"
                fields_attributes: [
                  {field_id: "nome_cliente", field_value: "%s"},
                  {field_id: "email_cliente", field_value: "%s"},
                  {field_id: "necessidade", field_value: "%s"},
                  {field_id: "data_reuniao", field_value: "%s"},
                  {field_id: "link_reuniao", field_value: "%s"}
                ]
              }) {
                card {
                  id
                  title
                  url
                }
              }
            }
            ''' % (
                self.pipe_id,
                self.phase_id,
                titulo,
                nome,
                email,
                dor.replace('"', '\\"').replace('\n', '\\n'),
                data_reuniao_formatada,
                event_link or ""
            )
            """
            
            response = requests.post(
                self.url,
                json={"query": mutation},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()

                if "errors" in result:
                    error_msg = result['errors'][0].get('message', 'Erro desconhecido')
                    print(f"Erro do Pipefy: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
                

                card = result.get("data", {}).get("createCard", {}).get("card", {})
                card_id = card.get("id")
                card_url = card.get("url")
                
                print(f"Card criado no Pipefy!")
                print(f"  ID: {card_id}")
                print(f"  URL: {card_url}")
                

                self._adicionar_comentario(card_id, nome, email, dor, data_reuniao_formatada, event_link)
                
                return {
                    "success": True,
                    "card_id": card_id,
                    "card_url": card_url
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro HTTP: {response.status_code}"
                }
                
        except Exception as e:
            print(f"Exceção ao criar card: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _adicionar_comentario(self, card_id: str, nome: str, email: str, 
                             dor: str, data_reuniao: str, event_link: str = None):
        """Adiciona um comentário no card com todos os detalhes"""
        try:
            texto_comentario = f"""
            📋 **Detalhes da Reunião**

            👤 **Cliente:** {nome}
            📧 **Email:** {email}
            📅 **Data/Hora:** {data_reuniao}

            💡 **Necessidade:**
            {dor}
            """
            if event_link:
                texto_comentario += f"\n🔗 **Link:** {event_link}"
            
            # Escapa caracteres especiais
            texto_escapado = texto_comentario.replace('"', '\\"').replace('\n', '\\n')
            
            mutation = """
            mutation {
              createComment(input: {
                card_id: "%s"
                text: "%s"
              }) {
                comment {
                  id
                }
              }
            }
            """ % (card_id, texto_escapado)
            
            response = requests.post(
                self.url,
                json={"query": mutation},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("Comentário adicionado ao card")
            else:
                print(f"Não foi possível adicionar comentário: {response.status_code}")
                
        except Exception as e:
            print(f"Erro ao adicionar comentário: {e}")
    
    def mover_card(self, card_id: str, nova_fase_id: str) -> bool:
        """Move um card para outra fase"""
        try:
            mutation = """
            mutation {
              moveCardToPhase(input: {
                card_id: "%s"
                destination_phase_id: "%s"
              }) {
                card {
                  id
                }
              }
            }
            """ % (card_id, nova_fase_id)
            
            response = requests.post(
                self.url,
                json={"query": mutation},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200 and "errors" not in response.json():
                print(f"Card movido para fase {nova_fase_id}")
                return True
            else:
                print(f"Erro ao mover card")
                return False
                
        except Exception as e:
            print(f"Erro ao mover card: {e}")
            return False


