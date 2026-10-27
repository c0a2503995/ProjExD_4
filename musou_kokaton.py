import math
import os
import random
import sys
import time
import pygame as pg

WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し,真理値タプルを返す関数
    引数：こうかとんや爆弾,ビームなどのRect
    戻り値：横方向,縦方向のはみ出し判定結果（画面内：True/画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て,dstがどこにあるかを計算し,方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite): #クラスの継承　他で定義した変数名をそのまま使える
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  # ★変更箇所: 無敵状態を管理する状態変数を追加
        self.hyper_life = 0    # ★変更箇所: 無敵状態の発動時間を管理する変数を追加

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]  # ★変更箇所: IndexErrorを防ぐためX方向の計算に修正
                sum_mv[1] += mv[1]  # ★変更箇所: IndexErrorを防ぐためY方向の計算に修正
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])  # ★変更箇所: sum_mv[0], sum_mv[1]に修正
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])  # ★変更箇所: sum_mv[0], sum_mv[1]に修正
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):  # ★変更箇所: sum_mv[0], sum_mv[1]に修正
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        # 追加機能4: 
        if self.state == "hyper":  # ★変更箇所: 無敵状態(hyper)のときの画像変更と時間経過の処理を追加
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"

        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"  # feature3 stateは爆弾の無効化と有効化を指す

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird,angle0:int):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        angle += angle0 ###Beamクラスのイニシャライザの引数に回転角度を追加しビームの回転角度に加算
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class NeoBeam(pg.sprite.Sprite):
    """
    散弾に関するクラス
    """
    def __init__(self, bird: Bird,num:int):
        """
        引数１　bird:　こうかとんクラス
        引数２　num :  ビームの数
        """
        self.num = num
        self.rect = bird.rect.center
        self.imag = bird.image
        self.bird = bird

    def gen_beams(self):
        beams = []
        step = int(100/self.num-1)
        for i in range(-50,+51,step):
            beams.append(Beam(self.bird,i))
            
        return beams


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]  # ★変更箇所: 強制終了エラーを防ぐためリストの0番目を指定
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら,_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Life:
    """
    ライフを表示する
    初期残機数：3
    爆弾に当たるたびに1減る
    画面右下に描画
    """
    def __init__(self, num: int):
        self.font = pg.font.Font(None, 40)
        self.color = (255, 0, 0)
        self.num = num
        self.image = pg.Surface((40, 40))
        self.image.set_colorkey((0, 0, 0))
        points = [(16*math.sin(t/100)**3 + 20,
                   -(13*math.cos(t/100)-5*math.cos(2*t/100)-2*math.cos(3*t/100)-math.cos(4*t/100)) + 20)
                  for t in range(0, 628)]
        pg.draw.polygon(self.image, self.color, points)
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH - 50, HEIGHT - 50)

    def update(self, screen: pg.Surface):
        for i in range(self.num):
            screen.blit(self.image, (WIDTH - 50 - i * 50, HEIGHT - 50))

class Gravity(pg.sprite.Sprite):
    """
    追加2:画面全体を覆う重力場に関するクラス
    """
    def __init__(self, life: int = 400):
        super().__init__()
        self.life = life
        # 画面全体を覆う透明度のある黒い矩形を生成
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)  # 半透明（透明度128）に設定
        self.rect = self.image.get_rect()

    def update(self):
        """
        重力場の発動時間を減算し、経過後は消去する
        """
        self.life -= 1
        if self.life < 0:
            self.kill()
class Defense_Wall(pg.sprite.Sprite):   #feature5
    """
    防御壁に関する関数
    """
    def __init__(self, bird: Bird, life: int):
        """
        ビーム画像Surfaceを生成する
        引数 bird：防御壁を置くこうかとん
        """
        super().__init__()
        width = 20
        height = bird.rect.height *2
        img0 = pg.Surface((width, height))
        pg.draw.rect(img0, (0,0,255), (0, 0, width, height))
        vx, vy = bird.dire
        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pg.transform.rotozoom(img0, angle, 1.0)
        self.image.set_colorkey((0, 0, 0)) 
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx

        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class EMP(pg.sprite.Sprite):  # feature3
    """
    発動時に存在する敵機と爆弾を無効化するクラス
    eキー押下かつスコアが20より大きいとスコアを20消費してempを使う
    """
    def __init__(self, enemy: pg.sprite.Group, bomb: pg.sprite.Group, screen: pg.Surface):
        """
        引数enemyは敵のグループ
        引数bombは爆弾のグループ
        引数screenは画面サーフェイス
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.fill((255, 255, 0))
        self.image.set_alpha(100)
        self.rect = self.image.get_rect()
        self.life = 3

        for teki in enemy:
            teki.interval = float("inf")
            teki.image = pg.transform.laplacian(teki.image)

        for bakudan in bomb:
            bakudan.speed //= 2
            bakudan.state = "inactive"

    def update(self):
        """
        empの時間を管理し、一定時間経過後黄色の矩形を消滅させる
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    life = Life(3)  # feature1  初期残機数を3にする
    dansuu = 3 #弾幕の数

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gras = pg.sprite.Group()  #追加2:重力場を管理するGroup
    emp = pg.sprite.Group()
    def_wall = pg.sprite.Group()

    print(type(bird))
    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:
                    beams.add(NeoBeam(bird,3).gen_beams())
                else:
                     beams.add(Beam(bird,0))

            if event.type == pg.KEYDOWN and event.key == pg.K_e:  # feature3
                if score.value > 20:
                    score.value -= 20
                    emp.add(EMP(emys, bombs, screen)) 
                    
            # 追加機能4: 
            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT:  # ★変更箇所: 右Shiftキーで無敵状態を発動
                if score.value > 100:
                    bird.state = "hyper"
                    bird.hyper_life = 500
                    score.value -= 100

            #追加2:発動判定
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value > 200:
                        gras.add(Gravity(400))
                        score.value -= 200  # スコアを200消費

            #追加5：防御壁
            if event.type == pg.KEYDOWN and event.key == pg.K_s:
                if score.value > 50 and len(def_wall) == 0:
                    score.value -= 50
                    def_wall.add(Defense_Wall(bird, 400))

        screen.blit(bg_img, [0, 0])  # ★変更箇所: 描画先の座標 [0, 0] を追加してエラーを修正

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト　#衝突したらどっちも消える
            score.value += 1  # 1点アップ　　　　　　　　　　　#削除したいときはTrue、残すときはFalse

        # 追加機能4
        for bomb in pg.sprite.spritecollide(bird, bombs, True): 
            
            if bird.state == "hyper":  # ★変更箇所: 無敵状態の場合はゲームオーバーにならず爆弾を消す
                exps.add(Explosion(bomb, 50)) 
                score.value += 1               
            else:  # ★変更箇所: 通常状態の場合は従来通りゲームオーバー処理
                life.num -= 1  #feature1 残機数を1減らす
                if life.num <= 0: #feature1 ライフが０になったら
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    return
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        #追加2:重力場と爆弾の衝突判定
        for bomb in pg.sprite.groupcollide(bombs, gras, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        #追加2:重力場と敵機の衝突判定
        for emy in pg.sprite.groupcollide(emys, gras, True, False).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10

        for bomb in pg.sprite.spritecollide(bird, bombs, False):  # こうかとんと衝突した爆弾リスト feature3:第三引数をFalseに変更した
            if bomb.state == "inactive":  # feature3 ifとelseの条件分岐を追加した
                bomb.kill()  # 通常の場合はelseが実行されるが、empで無効かされたらifを通る
            else:
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト 
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

        for bomb in pg.sprite.groupcollide(def_wall, bombs,True, True).keys():
            exps.add(Explosion(bomb, 50))

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        gras.update()  #追加2:重力場の更新
        gras.draw(screen)  #追加2:重力場の描画
        emp.update()  # feature3
        emp.draw(screen)  # feature3
        score.update(screen)
        life.update(screen) #feature1
        def_wall.draw(screen) #feature5
        def_wall.update()
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()