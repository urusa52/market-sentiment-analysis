"""5종 시각화를 생성한다.

실행: python -m scripts.04_make_charts
출력: outputs/ 디렉토리에 PNG 5개
"""

from src import visualize


if __name__ == "__main__":
    visualize.make_all_charts()
