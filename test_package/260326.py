import roslibpy
import numpy as np
import time
import pymysql
import json
from datetime import datetime
import pandas as pd

# [1] DB 설정
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '0000',  # 본인 비밀번호 확인
    'database': 'robot_db'
}

client = roslibpy.Ros(host='localhost', port=9090)
velocity_pub = roslibpy.Topic(client, '/turtle1/cmd_vel', 'geometry_msgs/Twist')


# [2] DB 저장 전용 함수 (밖으로 독립)
def save_to_mysql(ranges_list, action_name):
    try:
        # pymysql은 절대 로그인 창(GUI)을 띄우지 않습니다.
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        # SQL 실행 (기존과 동일)
        sql = "INSERT INTO lidardata (ranges, `when`, action) VALUES (%s, %s, %s)"
        val = (json.dumps(ranges_list), datetime.now(), action_name)

        cursor.execute(sql, val)
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ DB Error (pymysql): {e}")


def get_parsed_robot_data():
    try:
        # DB 연결
        conn = pymysql.connect(**DB_CONFIG)

        # [2] SQL 실행: ranges(JSON)와 action(정답)만 가져오기
        query = "SELECT ranges, action FROM lidardata"
        df_raw = pd.read_sql(query, conn)
        conn.close()

        print(f"📦 DB에서 {len(df_raw)}개의 데이터를 가져왔습니다.")

        # [3] JSON 파싱 로직
        parsed_list = []
        for index, row in df_raw.iterrows():
            # 문자열 형태의 JSON을 파이썬 리스트로 변환 (360개 요소)
            lidar_list = json.loads(row['ranges'])

            # 리스트 끝에 주행 액션(action) 추가 (총 361개)
            lidar_list.append(row['action'])

            parsed_list.append(lidar_list)

        # [4] 데이터프레임 생성 (컬럼명 설정)
        # 0도부터 359도까지의 이름과 마지막 'action' 컬럼명 생성
        column_names = [f"deg_{i}" for i in range(360)] + ["action"]
        df_final = pd.DataFrame(parsed_list, columns=column_names)

        return df_final

    except Exception as e:
        print(f"❌ 데이터 파싱 에러: {e}")
        return None


# --- 실행부 ---
df = get_parsed_robot_data()

if df is not None:
    # 상위 5개 데이터 확인
    print("\n✅ 데이터 파싱 완료! (상위 5행)")
    print(df.head())

    # 데이터 모양 확인 (행 개수, 361)
    print(f"\n📊 최종 데이터 모양: {df.shape}")

    # 넘파이 배열로 변환하고 싶다면?
    # numpy_data = df.values

def decide_motion(message):
    ranges_list = message.get('ranges', [])
    if len(ranges_list) < 360: return

    ranges = np.array(ranges_list)
    front = np.r_[ranges[350:360], ranges[0:10]]
    left = ranges[80:100]
    right = ranges[260:280]

    front_dist = np.mean(front)
    left_dist = np.mean(left)
    right_dist = np.mean(right)

    safe_dist = 0.5
    linear_v, angular_z = 0.0, 0.0

    if front_dist < safe_dist and right_dist < safe_dist:
        action = "turn_left"
        angular_z = 1.6
    elif front_dist < safe_dist and left_dist < safe_dist:
        action = "turn_right"
        angular_z = -1.6
    else:
        action = "go_forward"
        linear_v = 3.0

    print(f"F:{front_dist:.2f} -> {action}")

    # 거북이 조종 Publish
    msg = roslibpy.Message({
        'linear': {'x': float(linear_v), 'y': 0.0, 'z': 0.0},
        'angular': {'x': 0.0, 'y': 0.0, 'z': float(angular_z)}
    })
    velocity_pub.publish(msg)

    # [핵심] 여기서 DB 저장 함수를 '호출'합니다!
    save_to_mysql(ranges_list, action)


listener = roslibpy.Topic(client, '/scan', 'sensor_msgs/LaserScan')


def main():
    client.run()
    if client.is_connected:
        print("✅ 연결 성공 - 거북이 조종 시작")
        listener.subscribe(decide_motion)
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            client.terminate()


if __name__ == '__main__':
    main()