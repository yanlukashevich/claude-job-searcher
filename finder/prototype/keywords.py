# Keyword classification, v3.  ***THIS is the file you tune.***
#
# The axis is NOT difficulty. It is: "does this word say the offer is describing MY job?"
#   +3 CORE     the offer is describing my job
#   +1 CLOSE    the word carries no signal (git, jira, excel), or is one step from my stack
#   -1 UNKNOWN  the word says "a different KIND of developer" (postman -> manual QA,
#               helm -> platform, angular/rxjs -> the other frontend tribe). Not fatal, -1.
#   -3 OFF      a different profession
#   KILL        never, at any score
#
# Two kill sets, because a tool and a role are not the same thing. Figma on a React
# developer's skill list is a mockup he reads; "UX Designer" in the title is someone else's
# job. Same for security: "secure coding" on a .NET offer is a plus; "Security Engineer"
# in the title is a SOC job.
#
# Matched against requiredSkills + niceToHaveSkills + title, accent-folded.
# Edit the lists, then re-run  browse.py  and refresh offers.html.

# ------------------------------------------------- KILL, wherever it appears (skills or title)
KILL = """
sap  sap s/4hana  sap fi  sap sd  sap mm  abap
salesforce  apex  servicenow  microsoft dynamics  dynamics 365  power platform  power apps
power automate  uipath  sharepoint  microsoft sharepoint
cobol  mainframe  as/400  guidewire  gosu  murex  temenos  pega  sitecore  ferryt
unity  unreal
civil engineering  electrical engineering  architectural (engineering)  commissioning
qualification (pharma)  validation (pharma)  procurement  recruitment
german  french  spanish  deutsch
"""

# ------------------------------------------------- KILL, but ONLY in the title (a role, not a tool)
# Regexes: the title is prose. In the SKILLS field these same words are harmless or positive.
TITLE_KILL = r"""
\bux\b | \bui\s*/\s*ux\b | \bux\s*/\s*ui\b | \bdesigner\b | \bdesign\b | \buser experience\b
\bprojektant\b | \bgraphic\b | \bgrafik\b
\bsecurity\b | \bcyber\s*security\b | \bbezpiecze | \bsoc\b | \bpentest | \binfosec\b
\bpenetration tester\b | \bsecurity engineer\b | \bsecurity specialist\b
"""

# ------------------------------------------------- +3 CORE: on the CV / this is my job
CORE = """
c#  .net  .net core  .net c#  asp.net  asp.net core  entity framework  visual studio
react  reactjs  redux  next.js  typescript  javascript  html  html5  css  css3  scss
node.js  nest.js  express
python  fastapi  django  flask
azure  microsoft azure  azure devops  azure monitor
docker  ci/cd
sql  t-sql  ms sql  mssql  sql server  ms sql server  microsoft sql  microsoft sql server
postgresql  postresql  mysql
rest  rest api  restful api  api  api (application programming interface)  json  swagger
microservices  backend  frontend  oop  unit testing  software development
ai  artificial intelligence (ai)  llm  large language models  rag  genai  generative ai
openai  azure openai  prompt engineering  ai agents  ai tools  claude code
"""
# NOTE: the AI block is AI-that-ships-in-a-product. AI-that-gets-trained is in OFF.

# ------------------------------------------------- +1 CLOSE: no signal, or one step away
CLOSE = """
vue.js  graphql  mongodb  nosql  redis  databases  relational databases
oracle  oracle db  pl/sql  sql server management
jenkins  github actions  gitlab ci  devops  deployment  automation
aws  amazon aws  gcp  google cloud  google cloud platform  cloud  cloud computing  saas
bash  powershell  scripting  linux  linux / unix  unix  windows server  microsoft windows server
network  networking  tcp/ip  dns  dhcp  vpn  lan  active directory  active directory (ad)
cisco
troubleshooting  helpdesk  it support  customer support  incident management  itil  itsm
service management  network administration
security  cybersecurity  it security  network security  owasp  gdpr  devsecops  iam  oauth
pandas  numpy
testing  test automation  automated testing  functional testing  acceptance testing
test cases  test planning  test management  qa  quality assurance (qa)  manual testing
playwright  pytest  api testing
rabbitmq  system integration  architecture  system architecture
distributed systems  performance optimization  e-commerce
c  embedded  electronics
git  github  gitlab  bitbucket  maven
jira  atlassian jira  confluence  atlassian confluence  agile  scrum  kanban  safe  waterfall
sdlc  miro  documentation  communication  coordination  english  analytical thinking
analityczne myslenie  ms office  microsoft office  ms excel  microsoft excel  excel
microsoft powerpoint  office 365  microsoft 365  microsoft  microsoft platform
windows  microsoft windows  macos  hardware  maintenance  operations  training  ui  data
"""

# ------------------------------------------------- -1 UNKNOWN: a different KIND of developer
UNKNOWN = """
rust  go  golang  scala  groovy  perl  elixir  haskell  clojure
c++
langchain  llamaindex
terraform  iac  ansible  argocd  gitops  openshift  vmware  hyper-v  ldap  saml
entra id  elasticsearch  elk  grafana  prometheus  zabbix  nagios  sre
postman  soapui  selenium  selenium webdriver  robot framework  jmeter  k6  cucumber
istqb  testrail  appium  junit  jvm
esb  soa  yocto  rtos  vhdl  verilog
angular  cypress  jest  kafka  apache kafka  kubernetes  helm  rxjs
figma  sketch  ux/ui  ux  adobe xd
"""

# ------------------------------------------------- -3 OFF: a different profession
OFF = """
java  spring  spring boot  hibernate  kotlin
php  php 8  laravel  symfony  wordpress  ruby  ruby on rails
android  android studio  jetpack compose  ios  swift  swiftui  flutter  react native  mobile
machine learning  machine learning (ml)  ml  ai/ml  deep learning  pytorch  tensorflow
mlops  data science  nlp  vertex ai
power bi  dax  tableau  business intelligence (bi)  qlik  google analytics  looker
etl  datastage (etl)  big data  hadoop  spark  apache spark  pyspark  databricks  snowflake
bigquery  airflow  dbt  data modeling  data engineering  data integration  data analysis
analytics  data warehouse  hurtownie danych
business analysis  analiza biznesowa  uml  bpmn  system analysis  enterprise architect
project management  pmo  product management  product owner  scrum master  prince2  ms project
crm  erp  soap  xml  vba  r  excel macros
siem  microsoft sentinel  microsoft defender  splunk  firewall  penetration testing
risk management  kql  vulnerability
"""

def _set(s):
    return {w.strip() for w in s.replace("\n", "  ").split("  ") if w.strip()}

KILL, CORE, CLOSE, UNKNOWN, OFF = map(_set, (KILL, CORE, CLOSE, UNKNOWN, OFF))
WEIGHT = [(CORE, 3), (CLOSE, 1), (UNKNOWN, -1), (OFF, -3)]
TITLE_KILL = "|".join(p.strip() for p in TITLE_KILL.split("|") if p.strip())

if __name__ == "__main__":
    import re
    print("buckets:", {n: len(b) for n, b in [("KILL", KILL), ("+3 CORE", CORE),
          ("+1 CLOSE", CLOSE), ("-1 UNKNOWN", UNKNOWN), ("-3 OFF", OFF)]})
    dupes = [k for k in KILL | CORE | CLOSE | UNKNOWN | OFF
             if sum(k in b for b in (KILL, CORE, CLOSE, UNKNOWN, OFF)) > 1]
    print("in two buckets:", dupes or "none")
    re.compile(TITLE_KILL)
    print("TITLE_KILL compiles")
