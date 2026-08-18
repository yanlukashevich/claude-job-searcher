# Keyword classification, v5.  ***THIS is the file you tune.***
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
# job.
#
# So KILL is reserved for words that name a whole other CAREER (SAP, Salesforce, COBOL) --
# a word that can be item 9 of 10 on a normal developer's skill list belongs in OFF, where
# it costs -3 and the rest of the offer can outvote it. And TITLE_KILL entries must name a
# ROLE, not a domain: "Security Engineer" and "Solution Designer" are jobs Yan can do, while
# "SOC Analyst" and "UX Designer" are not.
#
# Matched against requiredSkills + niceToHaveSkills + title, accent-folded.
# Edit the lists, then re-run  browse.py  and refresh offers.html.

# ------------------------------------------------- KILL, wherever it appears (skills or title)
KILL = """
sap  sap s/4hana  sap fi  sap sd  sap mm  abap
salesforce  apex  servicenow  microsoft dynamics  dynamics 365
cobol  mainframe  as/400  guidewire  gosu  murex  temenos  pega  sitecore  ferryt
unity  unreal
german  french  spanish  deutsch
"""
# NOTE: the Microsoft low-code family (sharepoint, power apps/automate/platform, uipath) and
# the non-IT industry tags (pharma validation, procurement, civil engineering) moved to OFF.
# They were killing normal offers over one line of a ten-line skill list -- a React job that
# also lists Power Platform is still a React job. When they name the JOB they are in the
# title, and the veto catches that already.

# ------------------------------------------------- KILL, but ONLY in the title (a role, not a tool)
# Regexes: the title is prose. In the SKILLS field these same words are harmless or positive.
TITLE_KILL = r"""
\bux\s*/?\s*ui designer\b | \bui\s*/?\s*ux designer\b | \bux designer\b | \bui designer\b
\bux researcher\b | \bux writer\b | \buser experience\b | \bproduct designer\b
\bgraphic designer\b | \bvisual designer\b | \bweb designer\b | \bmotion designer\b
\bservice designer\b | \bgrafik\b | \bprojektant graficzn | \bdesigner graficzn
\bsoc\b | \bsoc analyst\b | \bpentest | \binfosec\b | \bpenetration tester\b
\bsecurity analyst\b | \bsecurity officer\b | \bsecurity operations\b | \bred team\b
\btester\b | \btesterka\b | \bqa\b | \bq\.a\.\b | \btest automation\b | \bautomation test
\btestow | \btesting engineer\b | \bsdet\b | \bquality assurance\b | \bquality engineer\b
\bhelpdesk\b | \bhelp desk\b | \bservice desk\b | \bsupport engineer\b | \bsupport specialist\b
\btechnical support\b | \bcustomer support\b | \bwsparcia technicznego\b | \bit support\b
"""

# ------------------------------------------------- +3 CORE: on the CV / this is my job
CORE = """
c#  .net  .net core  .net c#  asp.net  asp.net core  entity framework  visual studio
react  reactjs  next.js  typescript  javascript  html  html5  css  css3  scss
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
machine learning  machine learning (ml)  ml  ai/ml  deep learning  pytorch  tensorflow
mlops  data science  nlp  vertex ai  scikit-learn  hugging face  transformers
langchain  langgraph  llamaindex  embeddings  vector database  computer vision
"""
# NOTE: AI is CORE whether it ships in a product or gets trained. What stayed in OFF is the
# pipeline underneath it -- spark, airflow, dbt, snowflake are data ENGINEERING, another job.

# ------------------------------------------------- +1 CLOSE: no signal, or one step away
CLOSE = """
vue.js  graphql  redux  mongodb  nosql  redis  databases  relational databases
oracle  oracle db  pl/sql  sql server management
jenkins  github actions  gitlab ci  devops  deployment  automation
aws  amazon aws  gcp  google cloud  google cloud platform  cloud  cloud computing  saas
bash  powershell  scripting  linux  linux / unix  unix  windows server  microsoft windows server
network  networking  tcp/ip  dns  dhcp  vpn  lan  active directory  active directory (ad)
cisco
troubleshooting  incident management
owasp  gdpr  oauth
pandas  numpy  jupyter  matplotlib  statistics  statystyka
data analysis  analytics  data modeling  power bi  dax  google analytics
playwright  pytest
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
terraform  iac  ansible  argocd  gitops  openshift  vmware  hyper-v  ldap  saml
entra id  elasticsearch  elk  grafana  prometheus  zabbix  nagios  sre
postman  soapui  selenium  selenium webdriver  robot framework  jmeter  k6  cucumber
istqb  testrail  appium  junit  jvm
testing  test automation  automated testing  functional testing  acceptance testing
test cases  test planning  test management  qa  quality assurance (qa)  manual testing
api testing
business analysis  analiza biznesowa
helpdesk  it support  customer support  itil  itsm  service management  network administration
security  cybersecurity  it security  network security  devsecops  iam
esb  soa  yocto  rtos  vhdl  verilog
angular  cypress  jest  kafka  apache kafka  kubernetes  helm  rxjs
figma  sketch  ux/ui  ux  adobe xd
"""

# ------------------------------------------------- -3 OFF: a different profession
OFF = """
java  spring  spring boot  hibernate  kotlin
php  php 8  laravel  symfony  wordpress  ruby  ruby on rails
android  android studio  jetpack compose  ios  swift  swiftui  flutter  react native  mobile
tableau  business intelligence (bi)  qlik  looker
etl  datastage (etl)  big data  hadoop  spark  apache spark  pyspark  databricks  snowflake
bigquery  airflow  dbt  data engineering  data integration  data warehouse  hurtownie danych
uml  bpmn  system analysis  enterprise architect
project management  pmo  product management  product owner  scrum master  prince2  ms project
crm  erp  soap  xml  vba  r  excel macros
siem  microsoft sentinel  microsoft defender  splunk  firewall  penetration testing
risk management  kql  vulnerability
sharepoint  microsoft sharepoint  power platform  microsoft power platform  power apps
powerapps  power automate  power pages  dataverse  uipath  rpa  outsystems  low-code
civil engineering  electrical engineering  architectural (engineering)  commissioning
qualification (pharma)  validation (pharma)  procurement  recruitment
"""

def _set(s):
    return {w.strip() for w in s.replace("\n", "  ").split("  ") if w.strip()}

KILL, CORE, CLOSE, UNKNOWN, OFF = map(_set, (KILL, CORE, CLOSE, UNKNOWN, OFF))
WEIGHT = [(CORE, 3), (CLOSE, 1), (UNKNOWN, -1), (OFF, -3)]
# Both the newline and the " | " separate alternatives -- splitting on "|" alone glues the
# last pattern of each line to the first of the next, and silently kills both.
TITLE_KILL = "|".join(p.strip() for p in TITLE_KILL.replace(chr(10), "|").split("|") if p.strip())

if __name__ == "__main__":
    import re
    print("buckets:", {n: len(b) for n, b in [("KILL", KILL), ("+3 CORE", CORE),
          ("+1 CLOSE", CLOSE), ("-1 UNKNOWN", UNKNOWN), ("-3 OFF", OFF)]})
    dupes = [k for k in KILL | CORE | CLOSE | UNKNOWN | OFF
             if sum(k in b for b in (KILL, CORE, CLOSE, UNKNOWN, OFF)) > 1]
    print("in two buckets:", dupes or "none")
    re.compile(TITLE_KILL)
    print("TITLE_KILL compiles")
