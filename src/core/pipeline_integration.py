"""Complete PDF to Display pipeline integration."""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from src.analysis.pdf_processor import PDFProcessor
from src.analysis.claude_analyzer import ClaudeAnalyzer
from src.database.db_manager import DatabaseManager
from src.database.models import Problem, ProcessedFile

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of pipeline processing."""
    success: bool
    problems_extracted: int
    problems_analyzed: int
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    processing_time: float = 0.0


class PDFPipeline:
    """Manages the complete PDF → Processing → Display pipeline.
    
    This class orchestrates:
    1. PDF file detection and validation
    2. Problem extraction from PDFs
    3. Claude AI analysis of problems
    4. Storage in database
    5. Preparation for UI display
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize pipeline components."""
        self.db_manager = db_manager or DatabaseManager()
        self.pdf_processor = PDFProcessor()
        self.claude_analyzer = ClaudeAnalyzer()
        
    def process_pdf_file(self, pdf_path: str) -> PipelineResult:
        """Process a single PDF file through the complete pipeline.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PipelineResult with processing details
        """
        start_time = datetime.now()
        logger.info(f"Starting pipeline processing for: {pdf_path}")
        
        try:
            # Step 1: Validate file
            if not self._validate_pdf(pdf_path):
                return PipelineResult(
                    success=False,
                    problems_extracted=0,
                    problems_analyzed=0,
                    error_message="Invalid PDF file",
                    file_path=pdf_path
                )
                
            # Step 2: Check if already processed
            if self._is_already_processed(pdf_path):
                logger.info(f"File already processed: {pdf_path}")
                return PipelineResult(
                    success=True,
                    problems_extracted=0,
                    problems_analyzed=0,
                    error_message="File already processed",
                    file_path=pdf_path
                )
                
            # Step 3: Extract problems from PDF
            extraction_result = self._extract_problems(pdf_path)
            if not extraction_result['success']:
                return PipelineResult(
                    success=False,
                    problems_extracted=0,
                    problems_analyzed=0,
                    error_message=extraction_result['error'],
                    file_path=pdf_path
                )
                
            problems = extraction_result['problems']
            logger.info(f"Extracted {len(problems)} problems from PDF")
            
            # Step 4: Save to database and analyze each problem
            analyzed_count = 0
            saved_problems = []
            
            with self.db_manager.session_scope() as session:
                # Record processed file
                processed_file = ProcessedFile(
                    file_path=pdf_path,
                    filename=Path(pdf_path).name,
                    processed_at=datetime.now(),
                    problems_extracted=len(problems),
                    status='completed'
                )
                session.add(processed_file)
                
                # Process each problem
                for idx, problem_data in enumerate(problems):
                    try:
                        # Create problem record
                        problem = Problem(
                            original_text=problem_data['text'],
                            pdf_source=Path(pdf_path).name,
                            page_number=problem_data.get('page', 1),
                            difficulty=3,  # Default difficulty
                            category=problem_data.get('type', 'general')  # Default category
                        )
                        
                        # Analyze with Claude
                        analysis = self._analyze_problem(problem_data)
                        if analysis:
                            problem.translated_text = analysis.get('translated_text', '')
                            problem.difficulty = analysis.get('difficulty', 3)
                            # Mark as analyzed by setting translated_text
                            analyzed_count += 1
                            
                        session.add(problem)
                        saved_problems.append(problem)
                        
                    except Exception as e:
                        logger.error(f"Error processing problem {idx}: {e}")
                        continue
                        
                session.commit()
                
            # Step 5: Prepare for display
            display_ready_problems = self._prepare_for_display(saved_problems)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return PipelineResult(
                success=True,
                problems_extracted=len(problems),
                problems_analyzed=analyzed_count,
                file_path=pdf_path,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Pipeline error for {pdf_path}: {e}")
            return PipelineResult(
                success=False,
                problems_extracted=0,
                problems_analyzed=0,
                error_message=str(e),
                file_path=pdf_path
            )
            
    def _validate_pdf(self, pdf_path: str) -> bool:
        """Validate PDF file exists and is readable."""
        path = Path(pdf_path)
        
        if not path.exists():
            logger.error(f"File does not exist: {pdf_path}")
            return False
            
        if not path.suffix.lower() == '.pdf':
            logger.error(f"Not a PDF file: {pdf_path}")
            return False
            
        if path.stat().st_size == 0:
            logger.error(f"Empty file: {pdf_path}")
            return False
            
        return True
        
    def _is_already_processed(self, pdf_path: str) -> bool:
        """Check if file has already been processed."""
        try:
            with self.db_manager.session_scope() as session:
                existing = session.query(ProcessedFile).filter_by(
                    file_path=pdf_path,
                    status='completed'
                ).first()
                return existing is not None
        except Exception as e:
            logger.error(f"Error checking processed status: {e}")
            return False
            
    def _extract_problems(self, pdf_path: str) -> Dict[str, Any]:
        """Extract problems from PDF."""
        try:
            # Process PDF
            pages = self.pdf_processor.process_pdf(pdf_path)
            
            # Extract problems from all pages
            all_problems = []
            for page_num, page_content in enumerate(pages, 1):
                problems = self.pdf_processor.extract_problems(page_content)
                
                # Add page number to each problem
                for problem in problems:
                    problem['page'] = page_num
                    all_problems.append(problem)
                    
            return {
                'success': True,
                'problems': all_problems
            }
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {
                'success': False,
                'problems': [],
                'error': str(e)
            }
            
    def _analyze_problem(self, problem_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze single problem with Claude."""
        try:
            # Prepare problem for analysis
            problem_text = problem_data.get('text', '')
            
            # Skip if too short
            if len(problem_text.strip()) < 10:
                logger.warning("Problem text too short, skipping analysis")
                return None
                
            # Analyze with Claude
            analysis = self.claude_analyzer.analyze_problem(
                problem={'translated_text': problem_text, 'difficulty': 3},
                user_profile=None  # Use default profile
            )
            
            return {
                'translated_text': problem_text,
                'difficulty': analysis.difficulty_rating,
                'steps': [{'description': step.description} for step in analysis.steps],
                'hints': {
                    f'tier{i+1}': getattr(analysis.hints, f'tier{i+1}', '')
                    for i in range(3)
                }
            }
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return None
            
    def _prepare_for_display(self, problems: List[Problem]) -> List[Dict[str, Any]]:
        """Prepare problems for UI display."""
        display_problems = []
        
        for problem in problems:
            display_data = {
                'id': problem.id,
                'original_text': problem.original_text,
                'translated_text': problem.translated_text or problem.original_text,
                'difficulty': problem.difficulty,
                'page_number': problem.page_number,
                'source': 'pipeline',
                'is_analyzed': bool(problem.translated_text)
            }
            display_problems.append(display_data)
            
        return display_problems
        
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get pipeline processing statistics."""
        try:
            with self.db_manager.session_scope() as session:
                total_files = session.query(ProcessedFile).count()
                completed_files = session.query(ProcessedFile).filter_by(
                    status='completed'
                ).count()
                total_problems = session.query(Problem).count()
                analyzed_problems = session.query(Problem).filter(
                    Problem.translated_text != None
                ).count()
                
                return {
                    'total_files_processed': total_files,
                    'successfully_processed': completed_files,
                    'total_problems_extracted': total_problems,
                    'problems_analyzed': analyzed_problems,
                    'analysis_rate': (
                        analyzed_problems / total_problems * 100
                        if total_problems > 0 else 0
                    )
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}