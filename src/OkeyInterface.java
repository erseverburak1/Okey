import java.util.ArrayList;

public interface OkeyInterface {
    Tile chooseIndicator(ArrayList<Tile> allTiles);      // TUR:(Indicator:Gösterge)
    Tile chooseJoker(ArrayList<Tile> allTiles, Tile indicator);    // TUR:(Joker:Okey)
    ArrayList<Hand> dealTiles(ArrayList<Tile> allTiles); //Deals the tiles randomly for all 4 players (15-14-14-14).
    Hand bestHand(ArrayList<Hand> allHands);             //Decides the best hand for 4 players in the game.

}
