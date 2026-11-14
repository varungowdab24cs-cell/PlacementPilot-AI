from frontend.pages.assessment import _question_count


def test_question_count_for_no_available_questions() -> None:
    assert _question_count(0) == 0


def test_question_count_for_one_available_question_does_not_render_slider() -> None:
    def unexpected_slider(*args, **kwargs):
        raise AssertionError("The slider should not be rendered for one question")

    assert _question_count(1, slider=unexpected_slider) == 1


def test_question_count_for_multiple_questions_uses_expected_slider_bounds() -> None:
    calls = []

    def slider(*args, **kwargs):
        calls.append((args, kwargs))
        return 3

    assert _question_count(8, slider=slider) == 3
    assert calls == [
        (
            ("Questions in this benchmark",),
            {"min_value": 1, "max_value": 8, "value": 5},
        )
    ]
