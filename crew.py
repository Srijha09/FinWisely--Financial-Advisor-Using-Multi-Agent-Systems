from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool
from langchain_openai.chat_models import ChatOpenAI
from tools.yf_tech_analysis import YFinanceTechnicalAnalysisTool
from tools.yf_fundamental_analysis import YFinanceFundamentalAnalysisTool
from tools.sentiment_analysis import RedditSentimentAnalysisTool
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel
from langchain.tools import Tool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from dotenv import load_dotenv
import os
import yaml


# Environment Variables
load_dotenv()
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY")
os.environ["REDDIT_CLIENT_ID"] = os.getenv("REDDIT_CLIENT_ID")
os.environ["REDDIT_CLIENT_SECRET"] = os.getenv("REDDIT_CLIENT_SECRET")
os.environ["REDDIT_USER_AGENT"] = os.getenv("REDDIT_USER_AGENT")
api_key = os.getenv("OPENAI_API_KEY")
Model = "gpt-4o"
#llm = ChatOpenAI(api_key=api_key, model=Model)


with open('config/agents.yaml', 'r') as file:
    agents_config = yaml.safe_load(file)
with open('config/tasks.yaml', 'r') as file:
    tasks_config = yaml.safe_load(file)

class ResearchReport(BaseModel):
    researchreport: str
class TechnicalAnalysisReport(BaseModel):
    techsummary: str
class FundamentalAnalyisReport(BaseModel):
    summary: str
class FinancialReport(BaseModel):
    report: str

@CrewBase
class FinancialAdvisor:

    def __init__(self, agents_config, tasks_config, stock_symbol):
        self.agents_config = agents_config
        self.tasks_config = tasks_config
        self.stock_symbol = stock_symbol
        self.llm = ChatOpenAI(api_key=api_key, model=Model)
        self.serper_tool = SerperDevTool()
        self.reddit_tool = RedditSentimentAnalysisTool()
        self.yf_news_tool = Tool(
                name="yahoo_finance_news",
                func=lambda query: YahooFinanceNewsTool().run(query.replace("{stock_symbol}", self.stock_symbol)),
                description="Fetches the latest financial news from Yahoo Finance." )
        self.yf_tech_tool = YFinanceTechnicalAnalysisTool()
        self.yf_fundamental_tool = YFinanceFundamentalAnalysisTool()

    @agent
    def researcher(self) -> Agent:
        print(f"Stock Symbol Passed to Agent: {self.stock_symbol}")
        return Agent(
            config=self.agents_config['researcher'],
            verbose=True,
            memory=True,
            tools=[self.serper_tool,self.yf_news_tool],
            llm=self.llm,
            inputs={'stock_symbol': self.stock_symbol}
        )

    @task
    def research_task(self) -> Task:
        print(f"Stock Symbol Passed to Task: {self.stock_symbol}")
        return Task(
            config=self.tasks_config['research_task'],
            agent=self.researcher(),
            inputs={'stock_symbol': self.stock_symbol},
            output_json=ResearchReport
        )
    
    
    @agent
    def technical_analyst(self)-> Agent:
        return Agent( 
            config=self.agents_config['technical_analyst'],
            verbose=True,
            memory=True,
            tools=[self.yf_tech_tool],
            llm=self.llm,
            inputs={'stock_symbol': self.stock_symbol}

        )
    
    @task
    def technical_analysis_task(self) -> Task:
        print(f"Stock Symbol Passed to Task: {self.stock_symbol}")
        return Task(
            config=self.tasks_config['technical_analysis_task'],
            agent=self.technical_analyst(),
            inputs={'stock_symbol': self.stock_symbol},
            output_json=TechnicalAnalysisReport
            
        )
    
    
    @agent
    def fundamental_analyst(self)-> Agent:
        return Agent( 
            config=self.agents_config['fundamental_analyst'],
            verbose=True,
            memory=True,
            tools=[self.yf_fundamental_tool],
            llm=self.llm,
            inputs={'stock_symbol': self.stock_symbol}
        )

    @task
    def fundamental_analysis_task(self) -> Task:
        print(f"Stock Symbol Passed to Task: {self.stock_symbol}")
        return Task(
            config=self.tasks_config['fundamental_analysis_task'],
            agent=self.fundamental_analyst(),
            inputs={'stock_symbol': self.stock_symbol},
            output_json=FundamentalAnalyisReport
        )
    
    @agent
    def reporter(self)-> Agent:
        return Agent( 
            config=self.agents_config['reporter'],
            verbose=True,
            memory=True,
            tools=[self.reddit_tool, self.serper_tool, self.yf_fundamental_tool, self.yf_tech_tool, self.yf_news_tool],
            llm=self.llm,
            inputs={'stock_symbol': self.stock_symbol}
        )
    
    @task
    def report_task(self) -> Task:
        print(f"Stock Symbol Passed to Task: {self.stock_symbol}")
        return Task(
            config=self.tasks_config['report_task'],
            agent=self.reporter(),
            inputs={'stock_symbol': self.stock_symbol},
            output_json=FinancialReport
        )
    

    @crew
    def create_crew(self) -> Crew:
        """Creates the Stock Analysis Crew"""
        agents = [
            self.researcher(),
            self.technical_analyst(),
            self.fundamental_analyst(),
            self.reporter()
        ]
        tasks = [
            self.research_task(),
            self.technical_analysis_task(),
            self.fundamental_analysis_task(),
            self.report_task()
        ]
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )


def run_analysis(stock_symbol):
    # Instantiate the FinancialAdvisor class
    print(f"Running analysis for stock: {stock_symbol}")
    advisor = FinancialAdvisor(
        agents_config=agents_config,
        tasks_config=tasks_config,
        stock_symbol = stock_symbol
    )
    
    crew = advisor.create_crew()
    print("Crew created successfully")
    result = crew.kickoff(inputs={'stock_symbol': stock_symbol})
    return result

if __name__ == "__main__":
    analysis_result = run_analysis('AAPL')
    print("RESULT:", analysis_result)