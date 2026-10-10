"""Offline tests for schema_generator.py, which generates respectify-php's src/Schemas classes from schemas.py.

The PHP library supports PHP 7.4+, so the generated code must not use native enums, and Python str Enums
must become `string` properties. No API calls are made.
"""

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = REPO_ROOT / 'respectify' / 'schemas.py'
COMMITTED_PHP_SCHEMAS_DIR = REPO_ROOT.parent / 'respectify-php' / 'src' / 'Schemas'

# The CommentAssessment fields, as the generated PHP properties they should become
COMMENT_ASSESSMENT_PHP_PROPERTIES = [
    'public array $logicalFallacies;',
    'public array $objectionablePhrases;',
    'public array $negativeTonePhrases;',
    'public bool $appearsLowEffort;',
    'public int $overallScore;',
    'public float $toxicityScore;',
    'public string $toxicityExplanation;',
]


def _load_generator_module():
    spec = importlib.util.spec_from_file_location('schema_generator', REPO_ROOT / 'schema_generator.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def generated_php(tmp_path_factory) -> dict[str, str]:
    """Run the generator into a temp directory and return {file name: contents}."""
    output_dir = tmp_path_factory.mktemp('php_schemas')
    _load_generator_module().generate_php(SCHEMA_FILE, output_dir)
    return {path.name: path.read_text() for path in sorted(output_dir.glob('*.php'))}


class TestSchemaGeneratorPhp:

    def test_comment_score_is_generated(self, generated_php):
        assert 'CommentScore.php' in generated_php, "CommentScore extends CommentAssessment and must still be generated"

    def test_comment_score_has_assessment_fields(self, generated_php):
        comment_score_php = generated_php.get('CommentScore.php', '')
        for php_property in COMMENT_ASSESSMENT_PHP_PROPERTIES:
            assert php_property in comment_score_php, f"CommentScore should carry the inherited field: {php_property}"

    def test_comment_score_has_tolerance_fields(self, generated_php):
        comment_score_php = generated_php.get('CommentScore.php', '')
        assert 'public bool $exceedsTolerance;' in comment_score_php
        assert "$this->exceedsTolerance = $data['exceeds_tolerance'] ?? false;" in comment_score_php
        assert 'use Respectify\\Moderation\\ModerationTolerances;' in comment_score_php, \
            "CommentScore should use the hand-written Respectify\\Moderation\\ModerationTolerances"
        assert 'public ModerationTolerances $tolerances;' in comment_score_php
        assert "ModerationTolerances::fromApiResponse(" in comment_score_php, \
            "Tolerances should be built leniently from the response, as the hand-written class requires"

    def test_base_and_external_classes_are_not_generated(self, generated_php):
        # CommentAssessment is only a base class, never an API response by itself; ModerationTolerances
        # is hand-written in respectify-php's src/Moderation; enums are not classes in PHP 7.4
        for not_expected in ('CommentAssessment.php', 'ModerationTolerances.php',
                             'ModerationCategory.php', 'ToleranceLevel.php'):
            assert not_expected not in generated_php, f"{not_expected} should not be generated into src/Schemas"

    def test_megacall_result_builds_comment_score(self, generated_php):
        megacall_php = generated_php.get('MegaCallResult.php', '')
        assert 'public ?CommentScore $commentScore;' in megacall_php
        assert "$this->commentScore = isset($data['comment_score']) ? new CommentScore($data['comment_score']) : null;" \
            in megacall_php, "MegaCallResult must construct a CommentScore, not keep the raw array"

    def test_no_php_enum_types_are_emitted(self, generated_php):
        for file_name, php_code in generated_php.items():
            assert not re.search(r'^\s*enum\s', php_code, re.MULTILINE), f"{file_name} uses a PHP 8.1 enum"
            for enum_name in ('ModerationCategory', 'ToleranceLevel'):
                assert not re.search(rf'public \??{enum_name} \$', php_code), \
                    f"{file_name} types a property as the nonexistent PHP class {enum_name}"

    def test_str_enum_fields_become_strings(self, generated_php):
        for file_name in ('ObjectionablePhrase.php', 'NegativeTonePhrase.php'):
            php_code = generated_php.get(file_name, '')
            assert 'public string $category;' in php_code, f"{file_name} category should be a string"
            assert "$this->category = $data['category'] ?? '';" in php_code

    def test_constraint_constants_are_resolved(self, generated_php):
        for file_name in ('LogicalFallacy.php', 'ObjectionablePhrase.php', 'NegativeTonePhrase.php'):
            php_code = generated_php.get(file_name, '')
            assert 'FINDING_SEVERITY' not in php_code, f"{file_name} leaks a Python constant name into its docs"
            assert 'Constraints: ge=1, le=3' in php_code

    @pytest.mark.skipif(not COMMITTED_PHP_SCHEMAS_DIR.is_dir(), reason="respectify-php is not checked out alongside")
    def test_generated_files_match_respectify_php(self, generated_php):
        """Every generated file is committed in respectify-php byte for byte: the committed files are truly generated."""
        for file_name, php_code in generated_php.items():
            committed_file = COMMITTED_PHP_SCHEMAS_DIR / file_name
            assert committed_file.is_file(), f"{file_name} is generated but not committed in respectify-php"
            assert php_code == committed_file.read_text(), \
                f"{file_name} differs from respectify-php's committed copy; regenerate or fix the generator"

    @pytest.mark.skipif(shutil.which('php') is None, reason="php is not installed")
    def test_generated_files_are_valid_php(self, generated_php, tmp_path):
        for file_name, php_code in generated_php.items():
            php_file = tmp_path / file_name
            php_file.write_text(php_code)
            lint = subprocess.run(['php', '-l', str(php_file)], capture_output=True, text=True)
            assert lint.returncode == 0, f"{file_name} is not valid PHP: {lint.stdout}{lint.stderr}"
