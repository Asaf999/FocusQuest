"""Test PDF to Display pipeline integration."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.core.pipeline_integration import PDFPipeline, PipelineResult
from src.database.models import Problem, ProcessedFile


class TestPDFPipeline:
    """Test complete PDF processing pipeline."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = Mock()
        
        # Mock session scope
        mock_session = MagicMock()
        manager.session_scope = MagicMock(return_value=mock_session)
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        
        return manager, mock_session
    
    @pytest.fixture
    def pipeline(self, mock_db_manager):
        """Create pipeline with mocked components."""
        manager, _ = mock_db_manager
        with patch('src.core.pipeline_integration.PDFProcessor'):
            with patch('src.core.pipeline_integration.ClaudeAnalyzer'):
                pipeline = PDFPipeline(db_manager=manager)
                return pipeline
    
    def test_successful_pdf_processing(self, pipeline, mock_db_manager, tmp_path):
        """Test successful PDF processing through pipeline."""
        _, mock_session = mock_db_manager
        
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        # Mock PDF processor
        pipeline.pdf_processor.process_pdf = Mock(return_value=[
            "Page 1 content with problem"
        ])
        pipeline.pdf_processor.extract_problems = Mock(return_value=[
            {'text': 'Solve: 2x + 3 = 7', 'type': 'equation'}
        ])
        
        # Mock Claude analyzer
        mock_analysis = Mock()
        mock_analysis.difficulty_rating = 3
        mock_analysis.steps = [Mock(description="Step 1")]
        mock_analysis.hints = Mock(tier1="Hint 1", tier2="Hint 2", tier3="Hint 3")
        pipeline.claude_analyzer.analyze_problem = Mock(return_value=mock_analysis)
        
        # Mock database queries
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Process PDF
        result = pipeline.process_pdf_file(str(pdf_path))
        
        # Verify result
        assert result.success is True
        assert result.problems_extracted == 1
        assert result.problems_analyzed == 1
        assert result.error_message is None
        
        # Verify database operations
        assert mock_session.add.called
        assert mock_session.commit.called
        
    def test_invalid_pdf_handling(self, pipeline):
        """Test handling of invalid PDF files."""
        # Non-existent file
        result = pipeline.process_pdf_file("/path/to/nonexistent.pdf")
        assert result.success is False
        assert "Invalid PDF file" in result.error_message
        
    def test_already_processed_file(self, pipeline, mock_db_manager, tmp_path):
        """Test handling of already processed files."""
        _, mock_session = mock_db_manager
        
        # Create test PDF
        pdf_path = tmp_path / "processed.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        # Mock as already processed
        mock_processed = Mock(spec=ProcessedFile)
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_processed
        
        # Process PDF
        result = pipeline.process_pdf_file(str(pdf_path))
        
        # Should skip processing
        assert result.success is True
        assert result.problems_extracted == 0
        assert result.problems_analyzed == 0
        assert "already processed" in result.error_message
        
    def test_extraction_error_handling(self, pipeline, mock_db_manager, tmp_path):
        """Test handling of extraction errors."""
        _, mock_session = mock_db_manager
        
        # Create test PDF
        pdf_path = tmp_path / "error.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        # Mock extraction error
        pipeline.pdf_processor.process_pdf = Mock(
            side_effect=Exception("PDF parsing error")
        )
        
        # Mock database queries
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Process PDF
        result = pipeline.process_pdf_file(str(pdf_path))
        
        # Should handle error gracefully
        assert result.success is False
        assert result.problems_extracted == 0
        assert "PDF parsing error" in result.error_message
        
    def test_analysis_error_recovery(self, pipeline, mock_db_manager, tmp_path):
        """Test recovery from Claude analysis errors."""
        _, mock_session = mock_db_manager
        
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        # Mock PDF processor
        pipeline.pdf_processor.process_pdf = Mock(return_value=["Page 1"])
        pipeline.pdf_processor.extract_problems = Mock(return_value=[
            {'text': 'Problem 1'},
            {'text': 'Problem 2'}
        ])
        
        # Mock Claude analyzer to fail on first, succeed on second
        pipeline.claude_analyzer.analyze_problem = Mock(
            side_effect=[Exception("Claude error"), Mock(difficulty_rating=3)]
        )
        
        # Mock database
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Process PDF
        result = pipeline.process_pdf_file(str(pdf_path))
        
        # Should partially succeed
        assert result.success is True
        assert result.problems_extracted == 2
        assert result.problems_analyzed == 1  # Only second succeeded
        
    def test_prepare_for_display(self, pipeline):
        """Test problem preparation for UI display."""
        # Create test problems
        problems = [
            Problem(
                id=1,
                original_text="Problem 1",
                translated_text="Translated 1",
                difficulty=3,
                page_number=1,
                is_analyzed=True
            ),
            Problem(
                id=2,
                original_text="Problem 2",
                translated_text=None,  # No translation
                difficulty=4,
                page_number=2,
                is_analyzed=False
            )
        ]
        
        # Prepare for display
        display_data = pipeline._prepare_for_display(problems)
        
        # Verify format
        assert len(display_data) == 2
        
        # First problem
        assert display_data[0]['id'] == 1
        assert display_data[0]['translated_text'] == "Translated 1"
        assert display_data[0]['source'] == 'pipeline'
        assert display_data[0]['is_analyzed'] is True
        
        # Second problem (fallback to original)
        assert display_data[1]['id'] == 2
        assert display_data[1]['translated_text'] == "Problem 2"
        assert display_data[1]['is_analyzed'] is False
        
    def test_pipeline_statistics(self, pipeline, mock_db_manager):
        """Test getting pipeline processing statistics."""
        _, mock_session = mock_db_manager
        
        # Mock query results
        mock_session.query.return_value.count.side_effect = [10, 20, 15]
        mock_session.query.return_value.filter_by.return_value.count.side_effect = [8]
        
        # Get stats
        stats = pipeline.get_processing_stats()
        
        # Verify stats
        assert stats['total_files_processed'] == 10
        assert stats['successfully_processed'] == 8
        assert stats['total_problems_extracted'] == 20
        assert stats['problems_analyzed'] == 15
        assert stats['analysis_rate'] == 75.0
        
    def test_short_problem_text_skipped(self, pipeline):
        """Test that very short problem texts are skipped."""
        # Test short text
        result = pipeline._analyze_problem({'text': 'x = ?'})
        assert result is None
        
        # Test adequate text
        with patch.object(pipeline.claude_analyzer, 'analyze_problem') as mock_analyze:
            mock_analysis = Mock()
            mock_analysis.difficulty_rating = 3
            mock_analysis.steps = []
            mock_analysis.hints = Mock(tier1="", tier2="", tier3="")
            mock_analyze.return_value = mock_analysis
            
            result = pipeline._analyze_problem({'text': 'Solve the equation: 2x + 5 = 15'})
            assert result is not None
            assert result['difficulty'] == 3
            
    def test_processing_time_tracking(self, pipeline, mock_db_manager, tmp_path):
        """Test that processing time is tracked."""
        _, mock_session = mock_db_manager
        
        # Create test PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        # Mock quick processing
        pipeline.pdf_processor.process_pdf = Mock(return_value=["Page 1"])
        pipeline.pdf_processor.extract_problems = Mock(return_value=[])
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Process PDF
        result = pipeline.process_pdf_file(str(pdf_path))
        
        # Should track time
        assert result.processing_time > 0
        assert result.processing_time < 10  # Should be fast for empty PDF