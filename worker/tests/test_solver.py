from agent.solver import extract_latest_equation, verify_step


def test_valid_equivalent_step():
    result = verify_step("3*x + 5 = 20", "3*x = 15")
    assert result.valid is True


def test_scaled_equivalent_step():
    result = verify_step("x + 5 = 20", "2*x + 10 = 40")
    assert result.valid is True


def test_reordered_equivalent_step():
    result = verify_step("x = 15", "15 = x")
    assert result.valid is True


def test_invalid_step():
    result = verify_step("3*x + 5 = 20", "3*x = 20")
    assert result.valid is False


def test_extracts_latest_equation():
    message = "I started with 3x + 5 = 20 and then got 3x = 15"
    assert extract_latest_equation(message) == "3x = 15"
