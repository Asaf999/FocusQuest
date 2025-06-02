"""
PDF processing module for extracting Hebrew mathematical content
Handles RTL text, preserves LaTeX formulas, and segments problems
"""
import re
import os
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import pdfplumber
import pytesseract
from PIL import Image
import unicodedata


class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors"""
    pass


@dataclass
class PageContent:
    """Content from a single PDF page"""
    page_number: int
    text: str
    elements: List[Any] = field(default_factory=list)
    
    
@dataclass
class ExtractedProblem:
    """A single extracted mathematical problem"""
    problem_number: int
    page_number: int
    raw_text: str
    formulas: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize metadata after creation"""
        if not self.metadata:
            self.metadata = {
                'difficulty_estimate': self._estimate_difficulty(),
                'topic': self._detect_topic(),
                'formula_count': len(self.formulas)
            }
    
    def _estimate_difficulty(self) -> int:
        """Estimate problem difficulty based on content"""
        # Simple heuristic based on formula complexity
        if not self.formulas:
            return 1
        
        complexity_score = 0
        for formula in self.formulas:
            if formula.get('type') == 'integral':
                complexity_score += 3
            elif formula.get('type') == 'differential':
                complexity_score += 4
            elif formula.get('type') == 'partial_derivative':
                complexity_score += 5
            else:
                complexity_score += 1
                
        return min(5, max(1, complexity_score // 2))
    
    def _detect_topic(self) -> str:
        """Detect mathematical topic from content"""
        text_lower = self.raw_text.lower()
        
        if any(word in text_lower for word in ['גבול', 'limit', 'lim']):
            return 'limits'
        elif any(word in text_lower for word in ['אינטגרל', 'integral', '∫']):
            return 'integrals'
        elif any(word in text_lower for word in ['נגזרת', 'derivative', 'dy/dx', "f'"]):
            return 'derivatives'
        elif any(word in text_lower for word in ['דיפרנציאלי', 'differential']):
            return 'differential_equations'
        else:
            return 'general'


@dataclass
class PDFContent:
    """Complete content extracted from a PDF"""
    file_path: str
    pages: List[PageContent]
    page_count: int
    total_problems: int = 0
    
    def extract_problems(self) -> List[ExtractedProblem]:
        """Extract individual problems from the PDF content"""
        problems = []
        problem_number = 0
        
        for page in self.pages:
            # Split content by problem markers
            problem_patterns = [
                r'^\s*\d+\.',  # 1. 2. 3. etc
                r'^\s*[א-ת]\.',  # Hebrew letters
                r'^\s*\([א-ת]\)',  # (א) (ב) etc
                r'^\s*\(\d+\)',  # (1) (2) etc
                r'^בעיה\s*\d+',  # בעיה 1, בעיה 2
                r'^Problem\s*\d+',  # Problem 1, Problem 2
            ]
            
            combined_pattern = '|'.join(f'({p})' for p in problem_patterns)
            
            # Split text by problem markers
            lines = page.text.strip().split('\n')
            current_problem_lines = []
            found_problem_marker = False
            
            for line in lines:
                line_stripped = line.strip()
                if line_stripped and re.match(combined_pattern, line_stripped):
                    # Found new problem marker
                    if current_problem_lines and found_problem_marker:
                        # Save previous problem
                        problem_text = '\n'.join(current_problem_lines).strip()
                        if problem_text and self._contains_math_content(problem_text):
                            problem_number += 1
                            problem = self._create_problem(
                                problem_number, 
                                page.page_number, 
                                problem_text
                            )
                            problems.append(problem)
                    current_problem_lines = [line]
                    found_problem_marker = True
                elif line_stripped:
                    # For mixed content without explicit numbering, check if it's a new problem
                    if not found_problem_marker and self._contains_math_content(line_stripped):
                        # Start a new problem if we have accumulated lines
                        if current_problem_lines:
                            problem_text = '\n'.join(current_problem_lines).strip()
                            if problem_text and self._contains_math_content(problem_text):
                                problem_number += 1
                                problem = self._create_problem(
                                    problem_number,
                                    page.page_number,
                                    problem_text
                                )
                                problems.append(problem)
                            current_problem_lines = [line]
                        else:
                            current_problem_lines.append(line)
                    else:
                        current_problem_lines.append(line)
            
            # Don't forget the last problem
            if current_problem_lines:
                problem_text = '\n'.join(current_problem_lines).strip()
                if problem_text and self._contains_math_content(problem_text):
                    problem_number += 1
                    problem = self._create_problem(
                        problem_number,
                        page.page_number,
                        problem_text
                    )
                    problems.append(problem)
        
        self.total_problems = len(problems)
        return problems
    
    def _create_problem(self, number: int, page: int, text: str) -> ExtractedProblem:
        """Create a problem object with extracted formulas"""
        detector = FormulaDetector()
        formulas = detector.extract_all_formulas(text)
        
        return ExtractedProblem(
            problem_number=number,
            page_number=page,
            raw_text=text,
            formulas=formulas
        )
    
    def _contains_math_content(self, text: str) -> bool:
        """Check if text contains mathematical content"""
        # Skip title lines
        if 'תרגיל' in text and not any(c in text for c in ['=', '∫', 'f(x)']):
            return False
            
        math_indicators = [
            '=', '∫', '∑', 'lim', 'sin', 'cos', 'tan',
            'dx', 'dy', '²', '³', 'π', '∞',
            'f(x)', "f'(x)", '→'
        ]
        return any(indicator in text for indicator in math_indicators)


class FormulaDetector:
    """Detect and classify mathematical formulas"""
    
    def __init__(self):
        self.formula_patterns = {
            'integral': [r'∫', r'\\int', r'integral'],
            'differential': [r'\\frac\{dy\}\{dx\}', r'differential equation'],
            'derivative': [r'd[a-z]/d[a-z]', r"f'", r'\\frac\{d', r'derivative', r'נגזרת'],
            'partial_derivative': [r'∂', r'\\partial'],
            'limit': [r'lim', r'\\lim', r'→', r'\\to', r'גבול'],
            'summation': [r'∑', r'\\sum', r'Σ'],
            'function': [r'f\([^)]+\)\s*=', r'[a-z]\([^)]+\)\s*='],
            'equation': [r'[^=]+=\s*[^=]+$', r'=\s*0']
        }
        
        self.latex_unicode_map = {
            r'\alpha': 'α',
            r'\beta': 'β',
            r'\gamma': 'γ',
            r'\delta': 'δ',
            r'\epsilon': 'ε',
            r'\theta': 'θ',
            r'\lambda': 'λ',
            r'\mu': 'μ',
            r'\pi': 'π',
            r'\sigma': 'σ',
            r'\phi': 'φ',
            r'\omega': 'ω',
            r'\int': '∫',
            r'\sum': '∑',
            r'\infty': '∞',
            r'\partial': '∂',
            r'\nabla': '∇'
        }
    
    def is_formula(self, text: str) -> bool:
        """Check if text contains a mathematical formula"""
        # Check for mathematical symbols
        math_symbols = ['=', '∫', '∑', '∂', 'π', '∞', '≤', '≥', '∈', '∉', '⊂', '⊃', '∪', '∩']
        if any(symbol in text for symbol in math_symbols):
            return True
        
        # Check for function notation
        if re.search(r'[a-zA-Z]\([^)]+\)', text):
            return True
        
        # Check for derivatives
        if re.search(r'd[a-z]/d[a-z]', text) or "'" in text:
            return True
        
        # Check for common math terms
        math_terms = ['sin', 'cos', 'tan', 'log', 'ln', 'exp', 'lim', 'max', 'min']
        if any(term in text.lower() for term in math_terms):
            return True
        
        # Check for exponents
        if re.search(r'[x²³⁴⁵⁶⁷⁸⁹⁰¹]|\^|_', text):
            return True
        
        # Check if it's mostly Hebrew (not a formula)
        hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
        total_chars = len(text.strip())
        if total_chars > 0 and hebrew_chars / total_chars > 0.7:
            return False
            
        return False
    
    def extract_formula(self, text: str) -> str:
        """Extract and preserve formula exactly as written"""
        return text
    
    def classify_formula(self, formula: str) -> Dict[str, str]:
        """Classify the type of mathematical formula"""
        formula_lower = formula.lower()
        
        for formula_type, patterns in self.formula_patterns.items():
            for pattern in patterns:
                if re.search(pattern, formula_lower) or pattern in formula:
                    return {
                        'type': formula_type,
                        'latex': formula,
                        'original': formula
                    }
        
        # Default classification
        return {
            'type': 'general',
            'latex': formula,
            'original': formula
        }
    
    def complexity_score(self, formula: str) -> int:
        """Calculate complexity score for a formula"""
        score = 0
        
        # Count mathematical operations
        operations = ['∫', '∑', '∂', 'lim', '∏']
        for op in operations:
            score += formula.count(op) * 2
        
        # Count nested parentheses
        max_depth = 0
        current_depth = 0
        for char in formula:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1
        score += max_depth
        
        # Count special functions
        special_functions = ['sin', 'cos', 'tan', 'log', 'exp', 'sqrt']
        for func in special_functions:
            score += formula.lower().count(func)
        
        # Count subscripts/superscripts
        score += len(re.findall(r'[_^]', formula))
        
        # Count integral bounds
        if '∫' in formula:
            if re.search(r'∫[₀⁰]', formula) or re.search(r'\\int_', formula):
                score += 2
                
        # Additional complexity for special symbols
        if '∞' in formula:
            score += 2
        if '∇' in formula:
            score += 3
        if 'π' in formula:
            score += 1
            
        # Check for fractions
        if '/' in formula or '\\frac' in formula:
            score += 1
        
        return score
    
    def latex_to_unicode(self, latex: str) -> str:
        """Convert LaTeX symbols to Unicode"""
        result = latex
        for latex_sym, unicode_sym in self.latex_unicode_map.items():
            result = result.replace(latex_sym, unicode_sym)
        return result
    
    def extract_all_formulas(self, text: str) -> List[Dict[str, str]]:
        """Extract all formulas from text"""
        formulas = []
        
        # Split text into potential formula segments
        segments = re.split(r'[,;.]|\s{2,}', text)
        
        for segment in segments:
            segment = segment.strip()
            if segment and self.is_formula(segment):
                formula_info = self.classify_formula(segment)
                formulas.append(formula_info)
        
        return formulas


class PDFProcessor:
    """Main PDF processing class"""
    
    def __init__(self, use_ocr: bool = False):
        self.use_ocr = use_ocr
        
    def extract_content(self, pdf_path: str) -> PDFContent:
        """Extract content from PDF file"""
        try:
            # Check if file exists (will be skipped in mocked tests)
            if not os.path.exists(pdf_path):
                # Try to open anyway - might be mocked
                pass
                
            pages = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # If no text extracted and OCR is enabled, try OCR
                    if not text.strip() and self.use_ocr:
                        text = self._extract_with_ocr(page)
                    
                    page_content = PageContent(
                        page_number=i + 1,
                        text=text,
                        elements=[]
                    )
                    pages.append(page_content)
            
            return PDFContent(
                file_path=pdf_path,
                pages=pages,
                page_count=len(pages)
            )
            
        except FileNotFoundError:
            raise PDFProcessingError(f"PDF file not found: {pdf_path}")
        except Exception as e:
            raise PDFProcessingError(f"Error processing PDF: {str(e)}")
    
    def _extract_with_ocr(self, page) -> str:
        """Extract text using OCR for scanned pages with proper image cleanup"""
        image = None
        try:
            # Convert page to image
            image = page.to_image(resolution=300).original
            
            # Use pytesseract for OCR with Hebrew language support
            text = pytesseract.image_to_string(image, lang='heb+eng')
            
            return text
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            return ""
        finally:
            # Critical: Close PIL image to prevent memory leak
            if image is not None:
                try:
                    image.close()
                except:
                    pass  # Ignore errors during cleanup
    
    def is_rtl_text(self, text: str) -> bool:
        """Check if text is primarily right-to-left (Hebrew)"""
        if not text:
            return False
            
        # Count Hebrew vs Latin characters
        hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
        latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        
        # If more Hebrew than Latin, it's RTL
        return hebrew_chars > latin_chars