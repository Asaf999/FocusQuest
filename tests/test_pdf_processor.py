"""
Tests for Hebrew PDF processing with mathematical content preservation
Tests handle RTL text, LaTeX formulas, and mixed content
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import io

from src.analysis.pdf_processor import (
    PDFProcessor, PDFContent, ExtractedProblem,
    PDFProcessingError, FormulaDetector, PageContent
)


class TestPDFProcessor:
    """Test PDF processing functionality"""
    
    @pytest.fixture
    def pdf_processor(self):
        """Create a PDF processor instance"""
        return PDFProcessor()
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Mock PDF content for testing"""
        return """
        חשבון אינפיניטסימלי - תרגיל 5
        
        1. מצא את הגבול של f(x) = x² + 3x כאשר x → 2
        
        2. חשב את האינטגרל ∫sin(x)cos(x)dx
        
        3. פתור את המשוואה הדיפרנציאלית dy/dx = 2y
        """
    
    def test_basic_pdf_extraction(self, pdf_processor):
        """Test basic PDF text extraction"""
        # Create mock PDF file
        mock_pdf_path = "test.pdf"
        mock_text = "Test content with math: f(x) = x²"
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = mock_text
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = None
            mock_open.return_value = mock_pdf
            
            content = pdf_processor.extract_content(mock_pdf_path)
            
            assert isinstance(content, PDFContent)
            assert content.file_path == mock_pdf_path
            assert content.page_count == 1
            assert len(content.pages) == 1
            assert mock_text in content.pages[0].text
    
    def test_hebrew_text_extraction(self, pdf_processor):
        """Test extraction of Hebrew text"""
        hebrew_text = "מצא את הנגזרת של הפונקציה"
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = hebrew_text
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = None
            mock_open.return_value = mock_pdf
            
            content = pdf_processor.extract_content("hebrew.pdf")
            page_text = content.pages[0].text
            
            # Should contain Hebrew characters
            assert any('\u0590' <= char <= '\u05FF' for char in page_text)
            assert hebrew_text in page_text
    
    def test_mathematical_formula_detection(self):
        """Test detection and preservation of mathematical formulas"""
        detector = FormulaDetector()
        
        # Test various formula patterns
        test_cases = [
            ("f(x) = x² + 3x", True),
            ("∫sin(x)dx", True),
            ("dy/dx = 2y", True),
            ("lim x→∞", True),
            ("מצא את הגבול", False),  # Hebrew text, not formula
            ("x ∈ ℝ", True),
            ("∑_{i=1}^n i²", True),
            ("The answer is 42", False),  # Plain text
        ]
        
        for text, expected in test_cases:
            assert detector.is_formula(text) == expected
    
    def test_mixed_content_extraction(self, pdf_processor):
        """Test extraction of mixed Hebrew/English/Math content"""
        mixed_content = """
        בעיה 1: מצא את f'(x) כאשר f(x) = sin(x) + cos(x)
        The derivative of x³ is 3x²
        חשב: ∫₀^π sin(x)dx
        """
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = mixed_content
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = None
            mock_open.return_value = mock_pdf
            
            content = pdf_processor.extract_content("mixed.pdf")
            problems = content.extract_problems()
            
            assert len(problems) >= 1
            # Check that formulas are preserved in the extracted problem
            problem = problems[0]
            assert "sin(x)" in problem.raw_text
            assert "x³" in problem.raw_text or "x^3" in problem.raw_text
            assert "∫" in problem.raw_text
            # Check that all formulas were detected
            assert len(problem.formulas) >= 3
    
    def test_problem_segmentation(self, pdf_processor, sample_pdf_content):
        """Test segmentation of PDF into individual problems"""
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = sample_pdf_content
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = None
            mock_open.return_value = mock_pdf
            
            content = pdf_processor.extract_content("test.pdf")
            problems = content.extract_problems()
            
            assert len(problems) == 3
            for i, problem in enumerate(problems):
                assert problem.problem_number == i + 1
                assert problem.page_number == 1
                assert len(problem.raw_text) > 0
    
    def test_formula_preservation(self):
        """Test that mathematical formulas are preserved exactly"""
        formulas = [
            "f(x) = x² + 3x",
            "∫sin(x)cos(x)dx",
            "lim_{x→∞} (1 + 1/x)^x = e",
            "∑_{n=1}^∞ 1/n²",
        ]
        
        detector = FormulaDetector()
        for formula in formulas:
            extracted = detector.extract_formula(formula)
            assert extracted == formula
    
    def test_error_handling(self, pdf_processor):
        """Test error handling for invalid PDFs"""
        # Test non-existent file
        with pytest.raises(PDFProcessingError):
            pdf_processor.extract_content("non_existent.pdf")
        
        # Test invalid file type
        with patch('pdfplumber.open') as mock_open:
            mock_open.side_effect = Exception("Not a PDF")
            with pytest.raises(PDFProcessingError):
                pdf_processor.extract_content("invalid.txt")
    
    def test_ocr_fallback(self, pdf_processor):
        """Test OCR fallback for scanned PDFs"""
        # Test that OCR mode can be enabled
        processor_with_ocr = PDFProcessor(use_ocr=True)
        assert processor_with_ocr.use_ocr is True
        
        # Test OCR processing
        with patch('pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = "OCR extracted text: x² + y² = r²"
            
            with patch('pdfplumber.open') as mock_open:
                mock_pdf = MagicMock()
                mock_page = MagicMock()
                mock_page.extract_text.return_value = ""  # No text (scanned)
                mock_page.to_image.return_value.original = MagicMock()
                mock_pdf.pages = [mock_page]
                mock_pdf.__enter__.return_value = mock_pdf
                mock_pdf.__exit__.return_value = None
                mock_open.return_value = mock_pdf
                
                content = processor_with_ocr.extract_content("scanned.pdf")
                assert "x² + y² = r²" in content.pages[0].text
    
    def test_latex_formula_extraction(self):
        """Test extraction of LaTeX formulas"""
        latex_patterns = [
            (r"\int_0^\pi \sin(x) dx", "integral"),
            (r"\frac{dy}{dx} = 2y", "differential"),
            (r"\lim_{x \to \infty} f(x)", "limit"),
            (r"\sum_{i=1}^n i^2", "summation"),
        ]
        
        detector = FormulaDetector()
        for latex, formula_type in latex_patterns:
            result = detector.classify_formula(latex)
            assert result['type'] == formula_type
            assert result['latex'] == latex
    
    def test_hebrew_rtl_handling(self, pdf_processor):
        """Test proper handling of Hebrew RTL text"""
        rtl_text = "מצא את הגבול של הפונקציה"
        mixed_text = "חשב את f(x) = x² כאשר x = 3"
        
        # Verify RTL detection
        assert pdf_processor.is_rtl_text(rtl_text) is True
        assert pdf_processor.is_rtl_text("Hello world") is False
        assert pdf_processor.is_rtl_text(mixed_text) is True  # Mostly Hebrew
    
    def test_problem_metadata_extraction(self, pdf_processor, sample_pdf_content):
        """Test extraction of problem metadata"""
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = sample_pdf_content
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = None
            mock_open.return_value = mock_pdf
            
            content = pdf_processor.extract_content("test.pdf")
            problems = content.extract_problems()
            
            for problem in problems:
                assert hasattr(problem, 'metadata')
                assert 'difficulty_estimate' in problem.metadata
                assert 'topic' in problem.metadata
                assert 'formula_count' in problem.metadata


class TestFormulaDetector:
    """Test mathematical formula detection and classification"""
    
    @pytest.fixture
    def detector(self):
        return FormulaDetector()
    
    def test_basic_formula_detection(self, detector):
        """Test detection of basic mathematical formulas"""
        formulas = [
            "f(x) = x²",
            "y = mx + b",
            "∫f(x)dx",
            "∂f/∂x",
            "∑xᵢ",
        ]
        
        for formula in formulas:
            assert detector.is_formula(formula) is True
    
    def test_formula_type_classification(self, detector):
        """Test classification of formula types"""
        test_cases = [
            ("∫sin(x)dx", "integral"),
            ("df/dx", "derivative"),
            ("∂²f/∂x²", "partial_derivative"),
            ("lim x→0", "limit"),
            ("∑ᵢ₌₁ⁿ", "summation"),
            ("f(x) = x²", "function"),
            ("x² + 2x + 1 = 0", "equation"),
        ]
        
        for formula, expected_type in test_cases:
            result = detector.classify_formula(formula)
            assert result['type'] == expected_type
    
    def test_formula_complexity_scoring(self, detector):
        """Test formula complexity scoring for difficulty estimation"""
        simple_formulas = ["y = x", "f(x) = 2x", "x + 1"]
        complex_formulas = [
            "∫₀^∞ e^(-x²) dx",
            "∂²u/∂t² = c² ∇²u",
            "∑_{n=1}^∞ 1/n² = π²/6",
        ]
        
        for formula in simple_formulas:
            score = detector.complexity_score(formula)
            assert score < 5
            
        for formula in complex_formulas:
            score = detector.complexity_score(formula)
            assert score >= 5
    
    def test_latex_to_unicode_conversion(self, detector):
        """Test conversion between LaTeX and Unicode representations"""
        conversions = [
            (r"\alpha", "α"),
            (r"\beta", "β"),
            (r"\int", "∫"),
            (r"\sum", "∑"),
            (r"\infty", "∞"),
            (r"\partial", "∂"),
        ]
        
        for latex, unicode in conversions:
            assert detector.latex_to_unicode(latex) == unicode


class TestPDFIntegration:
    """Integration tests for complete PDF processing pipeline"""
    
    def test_full_pipeline(self):
        """Test complete pipeline from PDF to extracted problems"""
        processor = PDFProcessor()
        
        pdf_content = """
        חשבון אינפיניטסימלי - תרגיל 5
        
        1. מצא את הנגזרת של f(x) = sin(x)cos(x)
        2. חשב את האינטגרל ∫₀^π sin²(x)dx
        3. מצא את הגבול lim_{x→0} (sin(x)/x)
        4. פתור dy/dx + 2y = e^x
        """
        
        with patch('pdfplumber.open') as mock_open:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = pdf_content
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__.return_value = mock_pdf
            mock_pdf.__exit__.return_value = None
            mock_open.return_value = mock_pdf
            
            # Process PDF
            content = processor.extract_content("calculus.pdf")
            problems = content.extract_problems()
            
            # Verify extraction (may include title as problem)
            assert len(problems) >= 4
            
            # Check problem 1 (skipping 0 which might be title)
            p1 = next(p for p in problems if "sin(x)cos(x)" in p.raw_text)
            assert "sin(x)cos(x)" in p1.raw_text
            assert p1.formulas[0]['type'] == 'derivative'  # נגזרת means derivative
            
            # Check problem 2
            p2 = next(p for p in problems if "∫" in p.raw_text and "sin²(x)" in p.raw_text)
            assert "∫" in p2.raw_text
            assert p2.formulas[0]['type'] == 'integral'
            
            # Check problem 3
            p3 = next(p for p in problems if "lim" in p.raw_text)
            assert "lim" in p3.raw_text
            assert p3.formulas[0]['type'] == 'limit'
            
            # Check problem 4
            p4 = next(p for p in problems if "dy/dx" in p.raw_text and "2y" in p.raw_text)
            assert "dy/dx" in p4.raw_text
            assert p4.formulas[0]['type'] == 'derivative'
    
    def test_batch_processing(self):
        """Test processing multiple PDFs"""
        processor = PDFProcessor()
        
        pdf_contents = [
            "Test PDF 1\nProblem: Solve x² + 2x + 1 = 0",
            "Test PDF 2\nProblem: Solve x² + 3x + 1 = 0",
            "Test PDF 3\nProblem: Solve x² + 4x + 1 = 0",
        ]
        
        results = []
        for i, content in enumerate(pdf_contents):
            with patch('pdfplumber.open') as mock_open:
                mock_pdf = MagicMock()
                mock_page = MagicMock()
                mock_page.extract_text.return_value = content
                mock_pdf.pages = [mock_page]
                mock_pdf.__enter__.return_value = mock_pdf
                mock_pdf.__exit__.return_value = None
                mock_open.return_value = mock_pdf
                
                content_obj = processor.extract_content(f"test{i}.pdf")
                results.append(content_obj)
        
        # Verify all processed
        assert len(results) == 3
        for i, content in enumerate(results):
            assert content.page_count == 1
            problems = content.extract_problems()
            assert len(problems) >= 1