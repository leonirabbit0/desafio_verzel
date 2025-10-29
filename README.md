# Assistente Virtual Verzel - Roberto

Sistema de chatbot inteligente para agendamento automatizado de reuniões comerciais, integrando OpenAI, Google Calendar, Firebase e Pipefy.

## 📋 Sobre o Projeto

O **Roberto** é um assistente virtual desenvolvido para a Verzel que automatiza todo o processo de qualificação de leads e agendamento de reuniões comerciais. Através de uma conversa natural e guiada, o bot coleta informações essenciais do cliente, verifica disponibilidade de horários, agenda a reunião no Google Calendar e cria um card no Pipefy para acompanhamento do time comercial.


### 🌐 Demo Online

O projeto está disponível online com os seguintes serviços:
- **Frontend**: Hospedado na [Vercel](https://vercel.com)
- **Backend (API)**: Hospedado no [Railway](https://railway.app)

**🔗 Acesse a demo:** [https://desafio-verzel-m9k11wre3-elioenais-projects-3ad59b7b.vercel.app/](https://desafio-verzel-m9k11wre3-elioenais-projects-3ad59b7b.vercel.app/)


## 🚀 Funcionalidades

- **Conversa Inteligente**: Fluxo conversacional natural guiado por IA (GPT-4)
- **Qualificação de Leads**: Coleta nome, necessidade/dor do cliente, email e confirmação de interesse
- **Agendamento Automático**: Consulta horários disponíveis no Google Calendar e permite escolha
- **Integração Pipefy**: Criação automática de cards com todas as informações coletadas
- **Persistência**: Histórico completo de conversas armazenado no Firebase
- **Interface Responsiva**: Chat moderno e adaptável para desktop e mobile
- **Recuperação de Sessão**: Continuação automática de conversas interrompidas

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.x** com FastAPI
- **OpenAI API** (GPT-4 com Function Calling)
- **Firebase Firestore** (banco de dados)
- **Google Calendar API** (agendamento)
- **Pipefy API** (CRM)

### Frontend
- **React 18** com TypeScript
- **Vite** (build tool)
- **Framer Motion** (animações)
- **Lucide React** (ícones)
- **CSS-in-JS** (estilização inline)

## 📦 Estrutura do Projeto

```
.
├── app/
│   ├── database/
│   │   └── firebase.py          # Configuração Firebase
│   ├── routes/
│   │   └── routes.py            # Endpoints da API
│   └── services/
│       ├── openai_service.py    # Lógica do chatbot + Firebase
│       ├── google_service.py    # Integração Google Calendar
│       └── pipefy_service.py    # Integração Pipefy
├── src/
│   ├── components/
│   │   └── ChatInterface.tsx    # Interface do chat
│   ├── App.tsx                  # Componente principal
│   └── main.tsx                 # Entry point React
└── README.md
```

## ⚙️ Configuração e Instalação

### Pré-requisitos

- Python 3.8+
- Node.js 18+
- Conta Google Cloud (Calendar API)
- Conta OpenAI com acesso à API
- Conta Firebase
- Conta Pipefy

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd <nome-do-projeto>
```

### 2. Configuração do Backend

#### Instale as dependências Python:

```bash
pip install -r requirements.txt
```

#### Configure as variáveis de ambiente:

Crie um arquivo `.env` na raiz do projeto:

```env
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxx
VERZEL_ASSISTANT=asst_xxxxxxxxxxxxxxxxxx

# Google Calendar API
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxx
CLIENT_SECRET=app/config/client_secret.json
SCOPES=["https://www.googleapis.com/auth/calendar"]

# Pipefy
PIPEFY_API_KEY=eyJ0eXAiOiJKV1Qixxxxxxxxxx
PIPEFY_PIPE_ID=123456789
PIPEFY_PHASE_ID=340736206

# Google Token (gerado automaticamente após primeira autenticação)
GOOGLE_TOKEN=token.json
```

**Observações:**
- `SCOPES`: Lista de permissões do Google Calendar (já está no formato correto no código)
- `GOOGLE_TOKEN`: Arquivo gerado automaticamente após OAuth, não precisa configurar manualmente
- `CLIENT_SECRET`: Caminho para o arquivo de credenciais OAuth do Google Cloud

#### Configure o Firebase:

1. Crie um projeto no [Firebase Console](https://console.firebase.google.com/)
2. Baixe o arquivo de credenciais (`firebase_token.json`)
3. Coloque em `app/config/firebase_token.json`

#### Configure o Google Calendar:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto e ative a Google Calendar API
3. Baixe as credenciais OAuth 2.0
4. Na primeira execução, será necessário autenticar via navegador

### 3. Configuração do Frontend

#### Instale as dependências:

```bash
npm install
```

#### Configure a URL da API:

No arquivo `src/components/ChatInterface.tsx`, ajuste a constante `API_BASE_URL`:

```typescript
const API_BASE_URL = "http://localhost:8000"; // ou sua URL de produção
```

### 4. Execução

#### Backend (FastAPI):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (Vite):

```bash
npm run dev
```

O frontend estará disponível em `http://localhost:5173`

## 🔄 Fluxo de Funcionamento

1. **Boas-vindas**: Roberto se apresenta e inicia conversa
2. **Nome**: Solicita como o cliente gostaria de ser chamado
3. **Necessidade**: Pergunta sobre o problema/necessidade do cliente
4. **Confirmação**: Valida se o cliente deseja marcar uma reunião
5. **Horários**: Apresenta 5 opções de horários disponíveis
6. **Email**: Coleta email para envio do convite
7. **Agendamento**: Cria evento no Calendar e card no Pipefy
8. **Confirmação**: Envia link da reunião e mensagem de sucesso

## 🔌 Endpoints da API

### `GET /input_message`

Envia mensagem para o chatbot e recebe resposta.

**Parâmetros:**
- `message_received` (string): Mensagem do usuário
- `session_id` (string, opcional): ID da sessão

**Resposta:**
```json
{
  "session_id": "visitor_12345",
  "response": "Resposta do assistente"
}
```

### `GET /get_messages`

Recupera histórico de mensagens de uma sessão.

**Parâmetros:**
- `session_id` (string): ID da sessão

**Resposta:**
```json
{
  "messages": [
    {"role": "assistant", "content": "Olá!"},
    {"role": "user", "content": "Oi"}
  ]
}
```

## 🎨 Interface do Chat

- **Design moderno**: Gradiente azul, bordas arredondadas, sombras suaves
- **Animações**: Entrada suave de mensagens com Framer Motion
- **Responsivo**: Adapta-se perfeitamente a mobile e desktop
- **UX intuitiva**: Input com Enter para enviar, botão de envio visual
- **Scroll automático**: Acompanha novas mensagens
- **Persistência**: Recupera conversas anteriores automaticamente

## 🔒 Segurança

- Validação de email com regex
- Session IDs únicos e aleatórios
- Sanitização de entradas antes de salvar
- Tratamento robusto de erros
- Rate limiting (implementado pelo FastAPI)

## 📝 Observações Importantes

### Limitações Conhecidas

1. **Campos do Pipefy**: Atualmente os dados são salvos via comentário no card devido à estrutura dinâmica de campos. Para salvar diretamente nos campos, é necessário:
   - Executar `PipefyService().listar_campos()` para descobrir os IDs
   - Descomentar e ajustar o código alternativo em `pipefy_service.py`

2. **Timezone**: O sistema está configurado para UTC-3 (horário de Brasília). Ajuste conforme necessário.

3. **Horários Comerciais**: Slots disponíveis são gerados das 9h às 18h. Personalize em `google_service.py`.

### Melhorias Futuras

- [ ] Implementar webhooks para confirmação de presença
- [ ] Adicionar opção de reagendamento
- [ ] Suporte a múltiplos idiomas
- [ ] Dashboard administrativo
- [ ] Análise de sentimento nas conversas
- [ ] Exportação de relatórios

## 🐛 Solução de Problemas

### "Erro ao conectar com o servidor"
- Verifique se o backend está rodando
- Confirme a URL da API no frontend
- Verifique logs do FastAPI

### "Storage operation failed" no Firebase
- Confirme credenciais do Firebase
- Verifique regras de segurança do Firestore
- Valide estrutura de coleções

### "An error occurred" no Google Calendar
- Execute novamente para refazer autenticação OAuth
- Verifique se `token.json` tem permissões corretas
- Confirme que a API está ativada no Google Cloud

## 📄 Licença

Este projeto foi desenvolvido como parte de um desafio técnico.

## 👨‍💻 Autor

**Elioenai**

---

**Nota**: Este é um projeto de demonstração técnica. Certifique-se de revisar todas as configurações de segurança antes de uso em produção.
