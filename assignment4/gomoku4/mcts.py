from gtp_connection import format_point, point_to_coord
import random
import numpy as np
from board_util import (
    GoBoardUtil,
    BLACK,
    WHITE,
    EMPTY,
)

class MctsNode:
    def __init__(self, parent, move, color, boardsize):
        self.parent = parent
        self.children = []
        self.move = move
        self.wins = 0
        self.sims = 0
        self.boardsize = boardsize
        self.color = color  # color that just played

        if parent is None:
            # if node is root
            self.move_list = []
        else:
            self.move_list = parent.move_list.copy()
            self.move_list.append(move)

    def add_child(self, child):
        self.children.append(child)

    def update(self, wins, sims):
        self.wins += wins
        self.sims += sims

    def winrate(self):
        if self.sims == 0:
            return 0
        return self.wins / self.sims

    def __str__(self):
        return f"{format_point(point_to_coord(self.move, self.boardsize))} {self.wins}/{self.sims}"

    def __repr__(self, level=0):
        ret = "  " * level + str(self) + "\n"
        children = sorted(self.children, key=lambda n: n.winrate(), reverse=True)
        for child in children:
            ret += child.__repr__(level + 1)
        return ret


class MctsTree:
    def __init__(self, board, color, num_sims):
        self.board = board
        opp_color = GoBoardUtil.opponent(color)
        self.root = MctsNode(None, None, opp_color, board.size)
        self.color = color
        self.num_sims = num_sims

    def select(self):
        current = self.root
        while True:
            choices = [None] + current.children
            # for now, we are expanding a random node in the tree,
            # but later this will be replaced with a better tree policy based on uct
            next_node = random.choice(choices)
            if next_node is None:
                return current
            current = next_node

    def expand(self, node):
        # recreate board for that node
        board_copy = self.board.copy()
        for move in node.move_list:
            board_copy.play_move(move, board_copy.current_player)

        already_expanded_moves = list(map(lambda n: n.move, node.children))

        while True:
            # later this will be using a rule based policy to select the next child to expand
            next_move = GoBoardUtil.generate_random_move(board_copy, board_copy.current_player)
            if next_move not in already_expanded_moves:
                break

        board_copy.play_move(node.move, board_copy.current_player)
        opp_color = GoBoardUtil.opponent(node.color)
        new_node = MctsNode(node, next_move, opp_color, self.board.size)
        node.add_child(new_node)

        return new_node, board_copy

    def simulate(self, node, board_copy):
        wins = 0
        for i in range(self.num_sims):
            last_move = node.move

            moves_played = []
            winner = board_copy.check_win(last_move)

            while winner == EMPTY and len(board_copy.get_empty_points()) > 0:
                next_move = GoBoardUtil.generate_random_move(board_copy, board_copy.current_player)
                board_copy.play_move(next_move, board_copy.current_player)
                moves_played.append(next_move)
                last_move = next_move
                winner = board_copy.check_win(last_move)

            for move in moves_played:
                board_copy.undo_move(move)

            if winner == node.color:
                wins += 1
            elif winner == EMPTY:
                wins += 0.5

        return wins

    def back_propagate(self, node, wins):
        current = node
        while current is not None:
            current.update(wins, self.num_sims)
            wins = self.num_sims - wins
            current = current.parent

    def best_move(self):
        # because we are picking move randomly, we pick the node with the highest winrate
        # this needs to be changed to use the most pulled so far
        scores = list(map(lambda n: n.winrate(), self.root.children))
        max_score_index = np.argmax(scores)
        return self.root.children[max_score_index].move

    def __str__(self):
        return repr(self.root)


def mcts_step(mcts_tree):
    selected_node = mcts_tree.select()
    new_node, board_copy = mcts_tree.expand(selected_node)
    wins = mcts_tree.simulate(new_node, board_copy)
    mcts_tree.back_propagate(selected_node, wins)
