public class Tile {
    private Color color;
    private final int countNumber;//0-106 (mostly for arraylist operations)
    private int realNumber;//1-13 (actual number of tiles)

    public Tile(Color color, int countNumber, int realNumber) {
        this.color = color;
        this.countNumber = countNumber;
        this.realNumber = realNumber;
    }
    public Color getColor() { return color; }

    public int getCountNumber() {
        return countNumber;
    }

    public int getRealNumber() { return realNumber; }

    public void setRealNumber(int realNumber) {
        this.realNumber = realNumber;
    }

    public void setColor(Color color) {
        this.color = color;
    }

    @Override
    public String toString() {
        return "{"+color +
                ", " + realNumber +
                '}';
    }
}
