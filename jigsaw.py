import argparse
import math
import os
from PIL import Image, ImageTk
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame as pg

BG_COLOR = (44, 47, 51)

class Piece():
    # piece types
    TLC = 0
    TRC = 1
    BLC = 2
    BRC = 3
    BEE = 4
    TEE = 5
    BOE = 6
    TOE = 7
    ROE = 8
    LOE = 9
    REE = 10
    LEE = 11
    MID = 12
    MDR = 13

    def __init__(self, img, ptype, row, col, x_ext, y_ext):
        self.sprite = pg.image.fromstring(img.tobytes("raw", 'RGBA'), img.size, 'RGBA')
        self.w, self.h = img.size
        self.ptype = ptype
        self.row, self.col = row, col
        self.x_ext, self.y_ext = x_ext, y_ext
        self.x, self.y = 0, 0
        self.group = set([self])
        self.locked = False


    def sx(self):
        if self.ptype in (self.TRC, self.BRC, self.BEE,
                          self.TEE, self.ROE, self.MID):
            return self.x - self.x_ext
        else:
            return self.x


    def sy(self):
        if self.ptype in (self.BOE, self.REE, self.LEE, self.MDR):
            return self.y - self.y_ext
        else:
            return self.y


class Puzzle():
    def __init__(self, img_path, W, H, downscale=-1, margin=1):
        if W % 2 == 0 or H % 2 == 0: raise ValueError("Puzzle dimensions must be positive and odd")
        img = Image.open(img_path)
        img_w, img_h = img.size

        if downscale > 0 and max(img.size) > downscale:
            if img_w > img_h:
                img_h = int(img_h * downscale / img_w)
                img_w = downscale
            else:
                img_w = int(img_w * downscale / img_h)
                img_h = downscale
            img = img.resize((img_w, img_h))

        self.surface = pg.Surface((img_w * (margin * 2 + 1), img_h * (margin * 2 + 1)))
        self.origin_x, self.origin_y = img_w * margin, img_h * margin
        self.draw_order = list(range(W * H))

        piece_w, piece_h = img_w / W, img_h / H
        base_mask = Image.open("mask.png")
        base_mask_w, base_mask_h = base_mask.size
        mask_xscale = piece_w / base_mask_w;
        mask_yscale = piece_h / base_mask_h;

        corner_mask = Image.open("corner.png")
        ext = (corner_mask.size[0] - base_mask_w)
        x_ext = ext * mask_xscale
        y_ext = ext * mask_yscale

        self.W, self.H = W, H
        self.img, self.img_w, self.img_h = img, img_w, img_h
        self.piece_w, self.piece_h = piece_w, piece_h
        self.x_ext, self.y_ext = x_ext, y_ext
        self.connect_tol = min(piece_w, piece_h) / 5

        self.pieces = []
        self.matrix = {}
        for r in range(H):
            for c in range(W):
                if (r == 0 and c == 0):
                    # top left corner
                    ptype = Piece.TLC
                    mask = Image.open("corner_blur.png")
                    crop = img.crop((0, 0, piece_w + x_ext, piece_h))
                elif (r == 0 and c == W - 1):
                    # top right corner
                    ptype = Piece.TRC
                    mask = Image.open("corner_blur.png").transpose(Image.FLIP_LEFT_RIGHT)
                    crop = img.crop((img_w - piece_w - x_ext, 0, img_w, piece_h))
                elif (r == H - 1 and c == 0):
                    # bottom left corner
                    ptype = Piece.BLC
                    mask = Image.open("corner_blur.png").transpose(Image.FLIP_TOP_BOTTOM)
                    crop = img.crop((0, img_h - piece_h, piece_w + x_ext, img_h))
                elif (r == H - 1 and c == W - 1):
                    # bottom right corner
                    ptype = Piece.BRC
                    mask = Image.open("corner_blur.png").transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
                    crop = img.crop((img_w - piece_w - x_ext, img_h - piece_h, img_w, img_h))
                elif (r == 0 or r == H - 1):
                    # horizontal edge
                    if (c % 2 == 0):
                        mask = Image.open("even_edge_blur.png")
                        if (r == H - 1):
                            # bottom edge
                            ptype = Piece.BEE
                            mask = mask.transpose(Image.FLIP_TOP_BOTTOM)
                            crop = img.crop((c * piece_w - x_ext, img_h - piece_h, (c + 1) * piece_w + x_ext, img_h))
                        else:
                            # top edge
                            ptype = Piece.TEE
                            crop = img.crop((c * piece_w - x_ext, 0, (c + 1) * piece_w + x_ext, piece_h))
                    else:
                        mask = Image.open("odd_edge_blur.png")
                        if (r == H - 1):
                            # bottom edge
                            ptype = Piece.BOE
                            mask = mask.transpose(Image.FLIP_TOP_BOTTOM)
                            crop = img.crop((c * piece_w, img_h - piece_h - y_ext, (c + 1) * piece_w, img_h))
                        else:
                            # top edge
                            ptype = Piece.TOE
                            crop = img.crop((c * piece_w, 0, (c + 1) * piece_w, piece_h + y_ext))
                elif (c == 0 or c == W - 1):
                    # vertical edge (switch odd and even edges)
                    if (r % 2 == 0):
                        mask = Image.open("odd_edge_blur.png")
                        if (c == W - 1):
                            # right edge
                            ptype = Piece.ROE
                            mask = mask.transpose(Image.ROTATE_270)
                            crop = img.crop((img_w - piece_w - x_ext, r * piece_h, img_w, (r + 1) * piece_h))
                        else:
                            # left edge
                            ptype = Piece.LOE
                            mask = mask.transpose(Image.ROTATE_90)
                            crop = img.crop((0, r * piece_h, piece_w + x_ext, (r + 1) * piece_h))
                    else:
                        mask = Image.open("even_edge_blur.png")
                        if (c == W - 1):
                            # right edge
                            ptype = Piece.REE
                            mask = mask.transpose(Image.ROTATE_270)
                            crop = img.crop((img_w - piece_w, r * piece_h - y_ext, img_w, (r + 1) * piece_h + y_ext))
                        else:
                            # left edge
                            ptype = Piece.LEE
                            mask = mask.transpose(Image.ROTATE_90)
                            crop = img.crop((0, r * piece_h - y_ext, piece_w, (r + 1) * piece_h + y_ext))
                elif (r % 2 == c % 2):
                    ptype = Piece.MID
                    mask = Image.open("middle_blur.png")
                    crop = img.crop((c * piece_w - x_ext, r * piece_h,
                                    (c + 1) * piece_w + x_ext, (r + 1) * piece_h))
                else:
                    ptype = Piece.MDR
                    mask = Image.open("middle_blur.png").transpose(Image.ROTATE_90)
                    crop = img.crop((c * piece_w, r * piece_h - y_ext,
                                    (c + 1) * piece_w, (r + 1) * piece_h + y_ext))

                mask = mask.resize(crop.size)
                piece = Piece(Image.composite(crop, mask, mask), ptype, r, c, x_ext, y_ext)
                self.pieces.append(piece)
                self.matrix[(r, c)] = piece
                piece.x = c * piece_w + self.origin_x
                piece.y = r * piece_h + self.origin_y

    
    def click_check(self, x, y):
        for i in range(len(self.pieces) - 1, -1, -1):
            p = self.pieces[i]
            if (not p.locked and
                p.x < x < p.x + self.piece_w and
                p.y < y < p.y + self.piece_h):
                self.pieces.pop(i)
                self.pieces.append(p)
                return p
        return None
    
    def move_piece(self, piece, dx, dy):
        for p in piece.group:
            p.x = min(max(0, p.x + dx), self.surface.get_width() - self.piece_w)
            p.y = min(max(0, p.y + dy), self.surface.get_height() - self.piece_h)
            self.pieces.remove(p)
            self.pieces.append(p)
            
    
    def draw(self):
        self.surface.fill(BG_COLOR)
        pg.draw.rect(self.surface, (0, 0, 0), (self.origin_x, self.origin_y, self.img_w, self.img_h))
        for p in self.pieces:
            self.surface.blit(p.sprite, (p.sx(), p.sy()))

    def complete(self):
        return len(self.pieces[0].group) == self.W * self.H
    
    def connection_check(self, piece):
        def check_single(other, tx, ty):
            dx, dy = tx - piece.x, ty - piece.y
            if (abs(dx) < self.connect_tol and
                abs(dy) < self.connect_tol):
                self.move_piece(piece, dx, dy)
                new_group = piece.group.union(other.group)
                for p in new_group:
                    p.group = new_group
                    p.locked = other.locked

        n = self.matrix.get((piece.row - 1, piece.col), None)
        if n != None and n not in piece.group:
            check_single(n, n.x, n.y + self.piece_h)

        n = self.matrix.get((piece.row, piece.col - 1), None)
        if n != None and n not in piece.group:
            check_single(n, n.x + self.piece_w, n.y)

        n = self.matrix.get((piece.row + 1, piece.col), None)
        if n != None and n not in piece.group:
            check_single(n, n.x, n.y - self.piece_h)

        n = self.matrix.get((piece.row, piece.col + 1), None)
        if n != None and n not in piece.group:
            check_single(n, n.x - self.piece_w, n.y)
        
        def check_corner(tx, ty):
            if (abs(tx) < self.connect_tol and
                abs(ty) < self.connect_tol):
                self.move_piece(piece, tx, ty)
                for p in piece.group:
                    p.locked = True

        if (piece.row == 0):
            if (piece.col == 0):
                check_corner(self.origin_x - piece.x,
                             self.origin_y - piece.y)
            elif (piece.col == self.W - 1):
                check_corner(self.origin_x + self.img_w - self.piece_w - piece.x,
                             self.origin_y - piece.y)
        if (piece.row == self.H - 1):
            if (piece.col == 0):
                check_corner(self.origin_x - piece.x,
                             self.origin_y + self.img_h - self.piece_h - piece.y)
            elif (piece.col == self.W - 1):
                check_corner(self.origin_x + self.img_w - self.piece_w - piece.x,
                             self.origin_y + self.img_h - self.piece_h - piece.y)
        

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="""
Do a jigsaw puzzle. The port (default 7777) must be forwarded to host an online game.

    Start a 3x3 offline game:

        python3 jigsaw.py -o -i rock.png -s 3 3

    Join an online game:

        python3 jigsaw.py -c 8.8.8.8

    Host an 11x11 online game:

        python3 jigsaw.py -i itachi.png -s 11 11""")

    parser.add_argument('-o', '--offline', help="Play offline",
                        action='store_true', default=False)
    parser.add_argument('-c', '--connect', help="Connect to a puzzle server",
                        metavar='IP_ADDRESS', default=False)
    parser.add_argument('-p', '--port', help="Port to connect to or host from",
                        type=int, default=7777)
    parser.add_argument('-d', '--downscale', help="Downscale the resolution of the puzzle's largest dimension",
                        type=int, default=-1)
    parser.add_argument('-i', '--image', help="Image to make the puzzle out of",
                        default="")
    parser.add_argument('-s', '--size', help="Puzzle size (must be odd)",
                        nargs=2, type=int, default=False)
    args = parser.parse_args()

    pg.init()
    try:
        pg.mixer.init()
    except pg.error:
        pass
    display_flags = pg.RESIZABLE
    sw, sh = 1500, 1000
    screen = pg.display.set_mode([sw, sh], flags=display_flags)
    print("Building puzzle...")
    puzzle = Puzzle(args.image, args.size[0], args.size[1], downscale=args.downscale)
    print("Done.")
    pw, ph = puzzle.surface.get_width(), puzzle.surface.get_height()

    scale = min(sw / pw, sh / ph)
    scale_factor = 10 / 9

    panning = False
    pan_x = pw / 2 - sw / scale / 2
    pan_y = ph / 2 - sh / scale / 2

    holding = None

    running = True
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                elif event.key == pg.K_SPACE:
                    pan_x = pw / 2 - sw / scale / 2
                    pan_y = ph / 2 - sh / scale / 2
            elif event.type == pg.VIDEORESIZE:
                sw, sh = event.w, event.h
                screen = pg.display.set_mode([sw, sh], flags=display_flags)
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    holding = puzzle.click_check(pan_x + event.pos[0] / scale, pan_y + event.pos[1] / scale)
                elif event.button == 3:
                    panning = True
                elif event.button in (4, 5):
                    pan_x += sw / scale / 2
                    pan_y += sh / scale / 2
                    if event.button == 4:
                        scale *= scale_factor
                    else:
                        scale /= scale_factor
                    pan_x -= sw / scale / 2
                    pan_y -= sh / scale / 2
            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    if holding != None:
                        for p in holding.group:
                            puzzle.connection_check(p)
                        holding = None
                elif event.button == 3:
                    panning = False
            elif event.type == pg.MOUSEMOTION:
                mx = event.rel[0] / scale
                my = event.rel[1] / scale
                if panning:
                    pan_x -= mx
                    pan_y -= my
                if holding != None:
                    puzzle.move_piece(holding, mx, my)

        ss_width = min(max(1, sw / scale), pw)
        ss_height = min(max(1, sh / scale), ph)

        if pan_x < 0:
            ss_x = 0
            blit_x = int(-pan_x * scale)
        else:
            ss_x = min(pan_x, pw)
            blit_x = 0

        if pan_x > pw - ss_width:
            ss_width = max(pw - pan_x, 0)

        if pan_y < 0:
            ss_y = 0
            blit_y = int(-pan_y * scale)
        else:
            ss_y = min(pan_y, ph)
            blit_y = 0

        if pan_y > ph - ss_height:
            ss_height = max(ph - pan_y, 0)

        screen.fill(BG_COLOR)
        puzzle.draw()
        subsurf = puzzle.surface.subsurface(int(ss_x), int(ss_y), int(ss_width), int(ss_height))
        screen.blit(pg.transform.scale(subsurf, (int(ss_width * scale), int(ss_height * scale))), (blit_x, blit_y))
        pg.display.flip()
        
        if puzzle.complete() and pg.mixer.get_init() and not pg.mixer.music.get_busy():
            pg.mixer.music.load('congrats.wav')
            pg.mixer.music.Sound.set_volume(1)
            pg.mixer.music.play(-1)

    pg.quit()


if __name__ == "__main__":
    main()