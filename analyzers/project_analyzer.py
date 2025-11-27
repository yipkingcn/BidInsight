"""
项目内容分析器
使用 LangChain 和大模型（支持 OpenAI、Kimi 等）分析招标项目详情
提取项目建设内容、金额信息和分包详情
"""

import os
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


class PackageInfo(BaseModel):
    """分包信息"""
    package_name: str = Field(description="分包名称,如果没有明确说明则为'主包'")
    construction_content: str = Field(description="项目建设内容的简洁描述")
    amount_wan_yuan: Optional[float] = Field(
        default=None, 
        description="项目金额(万元),如果文本中没有提到具体金额则为null"
    )


class ProjectAnalysis(BaseModel):
    """项目分析结果"""
    overall_construction_content: str = Field(description="整体项目建设内容的简洁描述")
    overall_amount_wan_yuan: Optional[float] = Field(
        default=None,
        description="整体项目预算金额(万元),如果文本中没有提到则为null"
    )
    packages: List[PackageInfo] = Field(
        default_factory=list,
        description="分包列表,如果没有分包则只包含一个主包"
    )
    has_multiple_packages: bool = Field(
        default=False,
        description="是否有多个分包"
    )


class ProjectAnalyzer:
    """项目内容分析器"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "moonshot-v1-8k",
        temperature: float = 0.0
    ):
        """
        初始化分析器
        
        Args:
            api_key: API Key, 优先级: 参数 > MOONSHOT_API_KEY > OPENAI_API_KEY
            base_url: API Base URL, 如果不提供则从环境变量读取或使用默认值
                     - Kimi: https://api.moonshot.cn/v1 (默认)
                     - OpenAI: https://api.openai.com/v1
            model: 使用的模型名称
                   - Kimi 标准: moonshot-v1-8k (默认), moonshot-v1-32k, moonshot-v1-128k
                   - Kimi 推理: kimi-k2-thinking (支持思维链)
                   - OpenAI: gpt-4o-mini, gpt-4o, gpt-4-turbo
            temperature: 温度参数, 默认 0.0 (更确定性的输出)
        """
        # 支持多种环境变量名称
        self.api_key = (
            api_key 
            or os.getenv("MOONSHOT_API_KEY")  # Kimi 官方推荐
            or os.getenv("OPENAI_API_KEY")    # 兼容 OpenAI 格式
        )
        self.base_url = (
            base_url 
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.moonshot.cn/v1"  # 默认使用 Kimi
        )
        self.model = model
        self.temperature = temperature
        
        if not self.api_key:
            raise ValueError(
                "必须提供 api_key 参数或设置环境变量 MOONSHOT_API_KEY / OPENAI_API_KEY"
            )
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature
        )
        
        # 设置输出解析器
        self.parser = JsonOutputParser(pydantic_object=ProjectAnalysis)
        
        # 构建提示词模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的招标文件分析助手。你的任务是分析招标项目的"项目概况和招标范围"或"项目概况和采购范围"部分,提取关键信息。

请严格按照以下要求:
1. 提取整体项目的建设内容,用简洁的语言概括(50-200字)
2. 提取整体项目的预算金额,统一转换为**万元**单位
   - 如果原文是"元",除以10000转为万元
   - 如果原文是"千元",除以10转为万元
   - 如果原文是"万元",直接使用
   - 如果原文是"亿元",乘以10000转为万元
   - 如果没有提到金额,设为null
3. 判断是否有多个分包(如"第一包"、"第二包"、"标包1"等)
4. 如果有分包,为每个分包提取:
   - 分包名称
   - 该分包的建设内容
   - 该分包的金额(万元)
5. 如果没有明确的分包,则只提取主包信息

注意:
- 金额提取时要识别各种表述方式:"预算"、"最高限价"、"控制价"、"概算"等
- 建设内容要简洁明了,突出核心采购内容
- 返回的JSON必须符合格式要求

{format_instructions}
"""),
            ("user", """请分析以下招标项目内容:

{content}

请提取项目建设内容和金额信息。""")
        ])
        
        # 构建完整的链
        self.chain = self.prompt | self.llm | self.parser
    
    def analyze(self, content: str) -> ProjectAnalysis:
        """
        分析项目内容
        
        Args:
            content: 项目的"2.项目概况和招标范围"或"2.项目概况和采购范围"的文本内容
            
        Returns:
            ProjectAnalysis: 分析结果
        """
        # 预处理内容:去除多余空白,保留核心信息
        content = self._preprocess_content(content)
        
        # 调用 LLM 分析
        result = self.chain.invoke({
            "content": content,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return ProjectAnalysis(**result)
    
    def analyze_from_html(self, html_content: str) -> Optional[ProjectAnalysis]:
        """
        从完整的HTML内容中提取"2.项目概况"部分并分析
        
        Args:
            html_content: 完整的招标公告HTML内容
            
        Returns:
            ProjectAnalysis: 分析结果,如果无法提取相关内容则返回 None
        """
        # 提取"2. 项目概况和招标范围"或"2. 项目概况和采购范围"部分
        section_content = self._extract_section_2(html_content)
        
        if not section_content or len(section_content.strip()) < 50:
            return None
        
        return self.analyze(section_content)
    
    def _preprocess_content(self, content: str) -> str:
        """预处理内容"""
        # 去除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        # 统一空白字符
        content = re.sub(r'\s+', ' ', content)
        # 去除首尾空白
        content = content.strip()
        return content
    
    def _extract_section_2(self, html_content: str) -> Optional[str]:
        """
        从HTML中提取第2节内容
        支持多种格式:
        - 2. 项目概况和招标范围
        - 2.项目概况和招标范围
        - 2、项目概况和招标范围
        - 二、项目概况和招标范围
        - 2. 项目概况和采购范围
        """
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '\n', html_content)
        
        # 匹配多种格式的第2节标题
        patterns = [
            r'2[\s\.、）\)]\s*项目概况和招标范围(.*?)(?=3[\s\.、）\)]\s*|\n.*?[\d一二三四五六七八九十]+[\s\.、）\)]\s*|$)',
            r'2[\s\.、）\)]\s*项目概况和采购范围(.*?)(?=3[\s\.、）\)]\s*|\n.*?[\d一二三四五六七八九十]+[\s\.、）\)]\s*|$)',
            r'二、\s*项目概况和招标范围(.*?)(?=三、|\n.*?[一二三四五六七八九十]+、|$)',
            r'二、\s*项目概况和采购范围(.*?)(?=三、|\n.*?[一二三四五六七八九十]+、|$)',
            r'2[\s\.、）\)]\s*采购条件(.*?)(?=3[\s\.、）\)]\s*|\n.*?[\d一二三四五六七八九十]+[\s\.、）\)]\s*|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if len(content) > 50:  # 确保提取的内容有意义
                    return content
        
        return None


def create_analyzer(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "moonshot-v1-8k"
) -> ProjectAnalyzer:
    """
    创建分析器的便捷函数
    
    Args:
        api_key: API Key
        base_url: API Base URL (Kimi 默认: https://api.moonshot.cn/v1)
        model: 模型名称 (默认: moonshot-v1-8k)
        
    Returns:
        ProjectAnalyzer 实例
    """
    return ProjectAnalyzer(api_key=api_key, base_url=base_url, model=model)

