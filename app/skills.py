"""Skill dictionary used for resume / job-description matching.

Each line: canonical name | alias | alias ...
Matching is case-insensitive and whole-word (see analyzer.py).
"""

RAW_SKILLS = """
Python|python3
Java
JavaScript|js|ecmascript
TypeScript|ts
C++|cpp
C#|csharp
C Programming|c language
Go|golang
Rust
PHP
Ruby
Kotlin
Swift
R Programming|r language
MATLAB
SQL
Bash|shell scripting
HTML|html5
CSS|css3
React|react.js|reactjs
Next.js|nextjs
Vue|vue.js|vuejs
Angular|angularjs
Svelte
Redux
Tailwind CSS|tailwind
Bootstrap
Sass|scss
jQuery
Node.js|nodejs|node
Express|express.js|expressjs
FastAPI
Flask
Django
Spring Boot|springboot
Spring
.NET|dotnet|asp.net
Laravel
GraphQL
REST API|rest apis|restful|restful api|restful apis
Microservices|microservice
WebSockets|websocket
MongoDB|mongo
PostgreSQL|postgres
MySQL
SQLite
Redis
Firebase
Supabase
Elasticsearch
DynamoDB
Oracle
Cassandra
Git
GitHub
GitLab
Bitbucket
Docker
Kubernetes|k8s
Jenkins
CI/CD|cicd|ci cd
GitHub Actions
Terraform
Ansible
AWS|amazon web services
Azure
GCP|google cloud
Linux
Nginx
Heroku
Render
Vercel
Netlify
Machine Learning|ml
Deep Learning
Artificial Intelligence|ai
Natural Language Processing|nlp
Computer Vision
Generative AI|genai
LLM|llms|large language models
Prompt Engineering
RAG|retrieval augmented generation
LangChain
TensorFlow
PyTorch
Keras
scikit-learn|sklearn|scikit learn
spaCy
NLTK
Hugging Face|huggingface
OpenCV
Pandas
NumPy
SciPy
Matplotlib
Seaborn
Plotly
Streamlit
Jupyter|jupyter notebook
Data Analysis|data analytics
Data Visualization
Data Structures|dsa
Algorithms
Object Oriented Programming|oop|oops
Statistics
Feature Engineering
Power BI|powerbi
Tableau
Excel|microsoft excel|ms excel
Apache Spark|spark|pyspark
Hadoop
Kafka
Airflow
ETL
Big Data
Data Warehousing
Data Engineering
Data Science
MLOps
Android
iOS
React Native
Flutter
Figma
UI/UX|ui ux|ux design|ui design
Responsive Design
Web Development|full stack|full-stack|fullstack
Frontend|front-end|front end
Backend|back-end|back end
API Development|api design|api integration|apis
Unit Testing|unit tests
Test Automation
Selenium
Jest
PyTest|pytest
Postman
JUnit
Cypress
Agile
Scrum
Jira
Trello
Notion
Software Development Life Cycle|sdlc
System Design
Design Patterns
Cybersecurity|cyber security
Networking
OAuth
JWT
Authentication
Blockchain
Solidity
IoT
Embedded Systems
Arduino
Raspberry Pi
Verilog
VLSI
AutoCAD
SolidWorks
SEO
Digital Marketing
Content Writing
Project Management
Problem Solving
Communication|communication skills
Teamwork|team player|collaboration
Leadership
Critical Thinking
Time Management
Adaptability
Presentation Skills
Public Speaking
Analytical Skills|analytical thinking
Creativity
Debugging
Open Source|open-source
""".strip()


def load_skills():
    """Return {canonical: [aliases incl. canonical]} (all lower-case)."""
    skills = {}
    for line in RAW_SKILLS.splitlines():
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if not parts:
            continue
        canonical = parts[0]
        skills[canonical] = sorted({p.lower() for p in parts}, key=len, reverse=True)
    return skills


SKILLS = load_skills()

ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "created", "led", "managed",
    "improved", "optimized", "optimised", "automated", "deployed", "launched",
    "analyzed", "analysed", "engineered", "architected", "integrated", "reduced",
    "increased", "delivered", "collaborated", "organized", "organised", "mentored",
    "trained", "tested", "debugged", "migrated", "designed", "established",
    "coordinated", "streamlined", "researched", "wrote", "maintained", "achieved",
    "resolved", "configured", "contributed", "presented", "won", "secured",
}

STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers
him his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other
our out over own same she should so some such than that the their them then there these they this those through
to too under until up very was we were what when where which while who whom why will with would you your yours
able ability abilities strong good excellent preferred required requirements requirement responsibilities
responsibility role roles job position candidate candidates looking join company team teams work working works
including include includes etc must should plus years year experience experienced knowledge understanding
familiarity proficiency proficient skills skill using use used well ideal across within new within across
opportunity opportunities environment bachelor degree related field equivalent minimum least need needs
looking seeking successful ensure support help provide providing various multiple like day today based
motivated expected expect features feature practices practice product products software pipelines
intern interns internship internships join joining build builds building write writes follow follows
familiar familiarity preferred plus bonus nice highly passionate eager driven dynamic fast growing
responsible collaborate collaborating contribute contributing deliver delivering high quality
""".split())
