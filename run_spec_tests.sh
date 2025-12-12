#!/bin/bash
# Run all tests related to the pipeline-enhancement-and-output-parser spec

echo "Running spec-related tests..."
echo "=============================="
echo ""

# Core functionality tests
echo "1. Output Parser Tests..."
python -m pytest tests/test_output_parser.py -v --tb=no -q

echo ""
echo "2. Judge Output Parser Tests..."
python -m pytest tests/test_judge_output_parser.py -v --tb=no -q

echo ""
echo "3. Pipeline Config Tests..."
python -m pytest tests/test_pipeline_config.py -v --tb=no -q

echo ""
echo "4. Pipeline Runner Tests..."
python -m pytest tests/test_pipeline_runner.py -v --tb=no -q

echo ""
echo "5. Pipeline Evaluation Tests..."
python -m pytest tests/test_pipeline_evaluation.py -v --tb=no -q

echo ""
echo "6. Pipeline Examples Tests..."
python -m pytest tests/test_pipeline_examples.py -v --tb=no -q

echo ""
echo "7. Unified Evaluator Tests..."
python -m pytest tests/test_unified_evaluator.py -v --tb=no -q

echo ""
echo "8. Config Validation Tests..."
python -m pytest tests/test_config_validation.py -v --tb=no -q

echo ""
echo "9. Performance Monitoring Tests..."
python -m pytest tests/test_performance_monitoring.py -v --tb=no -q

echo ""
echo "10. Backward Compatibility Tests..."
python -m pytest tests/test_backward_compatibility.py -v --tb=no -q

echo ""
echo "11. Integration Tests - Judge..."
python -m pytest tests/test_integration_judge.py -v --tb=no -q

echo ""
echo "12. Integration Tests - Pipeline..."
python -m pytest tests/test_integration_pipeline.py -v --tb=no -q

echo ""
echo "13. Integration Tests - Pipeline Eval..."
python -m pytest tests/test_integration_pipeline_eval.py -v --tb=no -q

echo ""
echo "14. Integration Tests - Error Handling..."
python -m pytest tests/test_integration_error_handling.py -v --tb=no -q

echo ""
echo "=============================="
echo "Spec tests complete!"
