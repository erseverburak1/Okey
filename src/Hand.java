import java.util.List;

public class Hand {
    private final List<Tile> tiles;

    public Hand(List<Tile> tiles) {
        this.tiles = tiles;
    }

    public List<Tile> getTiles() {
        return tiles;
    }
}
