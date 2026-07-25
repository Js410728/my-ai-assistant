import pygame
import random
import sys

# 初始化Pygame
pygame.init()

# 游戏常量
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
CELL_SIZE = 40
GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE   # 16
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE  # 12

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (128, 128, 128)
YELLOW = (255, 255, 0)

# 方向常量
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# 子弹速度（像素/帧）
BULLET_SPEED = 8

class Wall(pygame.sprite.Sprite):
    """墙壁类，继承自pygame的Sprite"""
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.fill(GRAY)
        self.rect = self.image.get_rect()
        self.rect.x = x * CELL_SIZE
        self.rect.y = y * CELL_SIZE

class Bullet(pygame.sprite.Sprite):
    """子弹类"""
    def __init__(self, x, y, direction, owner):
        super().__init__()
        self.image = pygame.Surface((5, 5))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        self.direction = direction
        self.owner = owner  # 发射子弹的坦克，用于避免击中自己

    def update(self):
        # 根据方向移动
        self.rect.x += self.direction[0] * BULLET_SPEED
        self.rect.y += self.direction[1] * BULLET_SPEED

        # 超出屏幕则销毁
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()

class Tank(pygame.sprite.Sprite):
    """坦克基类"""
    def __init__(self, x, y, color, speed):
        super().__init__()
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.fill(color)
        # 画炮管（一个小矩形表示方向）
        self.gun = pygame.Surface((10, 4))
        self.gun.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.rect.x = x * CELL_SIZE
        self.rect.y = y * CELL_SIZE
        self.color = color
        self.speed = speed
        self.direction = UP  # 默认朝上
        self.last_shot_time = 0  # 上次射击时间（毫秒）
        self.shoot_cooldown = 500  # 射击冷却时间（毫秒）

    def update(self):
        # 更新炮管方向（由子类控制移动）
        # 这里只处理方向绘制，实际在draw中动态绘制更简单
        pass

    def draw(self, surface):
        # 绘制坦克主体
        surface.blit(self.image, self.rect)
        # 绘制炮管
        gun_rect = self.gun.get_rect()
        if self.direction == UP:
            gun_rect.midbottom = self.rect.center
        elif self.direction == DOWN:
            gun_rect.midtop = self.rect.center
        elif self.direction == LEFT:
            gun_rect.midright = self.rect.center
        elif self.direction == RIGHT:
            gun_rect.midleft = self.rect.center
        # 旋转炮管以匹配方向
        if self.direction == UP:
            gun = pygame.transform.rotate(self.gun, 90)
        elif self.direction == DOWN:
            gun = pygame.transform.rotate(self.gun, -90)
        elif self.direction == LEFT:
            gun = self.gun
        elif self.direction == RIGHT:
            gun = pygame.transform.rotate(self.gun, 180)
        surface.blit(gun, gun_rect)

    def can_shoot(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > self.shoot_cooldown:
            self.last_shot_time = now
            return True
        return False

    def shoot(self, bullet_group):
        if self.can_shoot():
            # 子弹出生位置在坦克中心
            bullet = Bullet(self.rect.centerx, self.rect.centery,
                            self.direction, self)
            bullet_group.add(bullet)

class PlayerTank(Tank):
    """玩家坦克，通过键盘控制"""
    def __init__(self, x, y):
        super().__init__(x, y, GREEN, 3)

    def update(self, walls_group, enemy_group):
        # 处理键盘输入
        keys = pygame.key.get_pressed()
        new_direction = self.direction
        if keys[pygame.K_UP]:
            new_direction = UP
        elif keys[pygame.K_DOWN]:
            new_direction = DOWN
        elif keys[pygame.K_LEFT]:
            new_direction = LEFT
        elif keys[pygame.K_RIGHT]:
            new_direction = RIGHT

        # 尝试移动
        self._move(new_direction, walls_group, enemy_group)

    def _move(self, new_direction, walls_group, enemy_group):
        # 保存原位置
        original_x, original_y = self.rect.x, self.rect.y
        # 更新方向
        self.direction = new_direction
        # 计算新位置
        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed

        # 边界限制
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # 碰撞检测：墙壁
        if pygame.sprite.spritecollide(self, walls_group, False):
            self.rect.x, self.rect.y = original_x, original_y
            return

        # 碰撞检测：敌方坦克（简单处理，不能重叠）
        if pygame.sprite.spritecollide(self, enemy_group, False):
            self.rect.x, self.rect.y = original_x, original_y
            return

class EnemyTank(Tank):
    """敌方坦克，简单AI"""
    def __init__(self, x, y):
        super().__init__(x, y, RED, 2)
        self.change_dir_time = pygame.time.get_ticks() + random.randint(500, 2000)
        self.shoot_time = pygame.time.get_ticks() + random.randint(1000, 3000)

    def update(self, walls_group, player_tank, bullet_group):
        now = pygame.time.get_ticks()
        # 随机改变方向
        if now > self.change_dir_time:
            self.direction = random.choice([UP, DOWN, LEFT, RIGHT])
            self.change_dir_time = now + random.randint(500, 2000)

        # 随机射击
        if now > self.shoot_time:
            self.shoot(bullet_group)
            self.shoot_time = now + random.randint(1000, 3000)

        # 移动
        original_x, original_y = self.rect.x, self.rect.y
        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed

        # 边界限制
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

        # 碰撞墙壁或玩家坦克
        if (pygame.sprite.spritecollide(self, walls_group, False) or
                (player_tank and self.rect.colliderect(player_tank.rect))):
            self.rect.x, self.rect.y = original_x, original_y
            # 如果碰到障碍，换方向
            self.direction = random.choice([UP, DOWN, LEFT, RIGHT])

class Game:
    """游戏主类"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("坦克大战简化版")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.reset_game()

    def reset_game(self):
        """重置游戏状态"""
        # 创建精灵组
        self.all_sprites = pygame.sprite.Group()
        self.walls_group = pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group()
        self.enemy_group = pygame.sprite.Group()
        self.player = None

        # 创建墙壁（简单示例：四周和中间一些砖块）
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                # 边界墙壁
                if x == 0 or x == GRID_WIDTH-1 or y == 0 or y == GRID_HEIGHT-1:
                    wall = Wall(x, y)
                    self.walls_group.add(wall)
                    self.all_sprites.add(wall)
                # 内部随机一些墙壁（约20%）
                elif random.random() < 0.2:
                    wall = Wall(x, y)
                    self.walls_group.add(wall)
                    self.all_sprites.add(wall)

        # 创建玩家坦克（位于底部中间）
        player_x = GRID_WIDTH // 2
        player_y = GRID_HEIGHT - 2
        self.player = PlayerTank(player_x, player_y)
        self.all_sprites.add(self.player)

        # 创建敌方坦克（顶部随机位置）
        for _ in range(4):
            while True:
                x = random.randint(1, GRID_WIDTH-2)
                y = random.randint(1, 3)
                # 确保不与墙壁重叠
                test_rect = pygame.Rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if not any(wall.rect.colliderect(test_rect) for wall in self.walls_group):
                    enemy = EnemyTank(x, y)
                    self.enemy_group.add(enemy)
                    self.all_sprites.add(enemy)
                    break

        self.score = 0
        self.lives = 3
        self.game_over = False
        self.win = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.player and not self.game_over:
                        self.player.shoot(self.bullets_group)
                elif event.key == pygame.K_r:
                    self.reset_game()
                elif event.key == pygame.K_q:
                    return False
        return True

    def update(self):
        if self.game_over or self.win:
            return

        # 更新玩家
        self.player.update(self.walls_group, self.enemy_group)

        # 更新敌方坦克
        for enemy in self.enemy_group:
            enemy.update(self.walls_group, self.player, self.bullets_group)

        # 更新子弹
        self.bullets_group.update()

        # 子弹与墙壁碰撞
        for bullet in self.bullets_group:
            hit_walls = pygame.sprite.spritecollide(bullet, self.walls_group, True)
            if hit_walls:
                bullet.kill()
                # 墙壁被摧毁后从all_sprites中移除
                for wall in hit_walls:
                    self.all_sprites.remove(wall)

        # 子弹与敌方坦克碰撞
        for bullet in self.bullets_group:
            if bullet.owner == self.player:  # 只有玩家子弹才能消灭敌人
                hit_enemies = pygame.sprite.spritecollide(bullet, self.enemy_group, True)
                if hit_enemies:
                    bullet.kill()
                    self.score += len(hit_enemies)
                    for enemy in hit_enemies:
                        self.all_sprites.remove(enemy)

        # 子弹与玩家碰撞（敌方子弹击中玩家）
        for bullet in self.bullets_group:
            if bullet.owner != self.player and self.player.rect.colliderect(bullet.rect):
                bullet.kill()
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True
                    self.player.kill()
                else:
                    # 玩家重生（简单处理：回到初始位置）
                    self.player.rect.x = (GRID_WIDTH // 2) * CELL_SIZE
                    self.player.rect.y = (GRID_HEIGHT - 2) * CELL_SIZE

        # 检查胜利条件
        if len(self.enemy_group) == 0:
            self.win = True

    def draw(self):
        self.screen.fill(BLACK)
        # 绘制所有精灵（墙壁、坦克）
        self.all_sprites.draw(self.screen)
        # 绘制子弹
        self.bullets_group.draw(self.screen)
        # 绘制每个坦克的炮管（因为炮管是额外绘制的）
        if self.player:
            self.player.draw(self.screen)
        for enemy in self.enemy_group:
            enemy.draw(self.screen)

        # 显示得分和生命
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        lives_text = self.font.render(f"Lives: {self.lives}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        self.screen.blit(lives_text, (10, 50))

        # 游戏结束或胜利信息
        if self.game_over:
            over_text = self.font.render("GAME OVER - Press R to restart, Q to quit", True, RED)
            text_rect = over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(over_text, text_rect)
        elif self.win:
            win_text = self.font.render("YOU WIN! - Press R to restart, Q to quit", True, GREEN)
            text_rect = win_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(win_text, text_rect)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)  # 60帧
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
    