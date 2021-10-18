import java.util.ArrayList;
import java.util.Collections;
import java.util.concurrent.ThreadLocalRandom;

public class OkeyGame implements OkeyInterface{

    ArrayList<Tile> allTiles;                       //every tile with order
    private final static int numberOfTiles = 106;

    public OkeyGame(ArrayList<Tile> allTiles) {
        this.allTiles = allTiles;
    }

    @Override
    public Tile chooseIndicator(ArrayList<Tile> allTiles) {
        int randomNum = ThreadLocalRandom.current().nextInt(0, 105);   //randomly chosing the indicator.
        if(allTiles.get(randomNum).getColor()==Color.GREEN){ // if it is the indicator the next tile will be the joker.
            randomNum++;
        }
        return allTiles.get(randomNum);
    }

    @Override
    public Tile chooseJoker(ArrayList<Tile> allTiles, Tile indicator) {           //indicator +1 will be joker.
        for(int i =0;i<numberOfTiles;i++){                  // setting false joker
            if(allTiles.get(i).getColor()==Color.GREEN){
                allTiles.get(i).setRealNumber(indicator.getRealNumber()+1);
                allTiles.get(i).setColor(indicator.getColor());
            }
        }
        if(indicator.getRealNumber()==13){
            return new Tile(indicator.getColor(), 999, 1);
        }
        return new Tile(indicator.getColor(), 999, indicator.getRealNumber()+1);
    }

    @Override
    public ArrayList<Hand> dealTiles(ArrayList<Tile> allTiles) {
        Collections.shuffle((allTiles));                //shuffling all tiles
        ArrayList<Hand> allHands = new ArrayList<>();
        Hand hand1 = new Hand(allTiles.subList(0,15));  // first player to play gets 15 tiles.
        Hand hand2 = new Hand(allTiles.subList(15,29)); // others get 14.
        Hand hand3 = new Hand(allTiles.subList(29,43));
        Hand hand4 = new Hand(allTiles.subList(43,57));
        allHands.add(hand1);
        allHands.add(hand2);
        allHands.add(hand3);
        allHands.add(hand4);
        return allHands;
    }

    @Override
    public Hand bestHand(ArrayList<Hand> allHands) {
        // not implemented yet
        //it can be calculated with first finding all possibilities within each hand
        //traversing with list of lists for tiles
        //tiles that are the same color will be reached with modulo 13 (yellow1%13=0 , red1%13=0)
        //tiles with consecutive values can be reached with +1
        return null;
    }

    public ArrayList<ArrayList<Tile>> sameColors (){
        ArrayList<Hand> allHands = dealTiles(allTiles);
        ArrayList<ArrayList<Tile>>sameColors = new ArrayList<>();
        for(int i =0;i<4;i++) {
            for (int j = 0; j < allHands.get(i).getTiles().size(); j++) {
                sameColors.add((ArrayList<Tile>) allHands.get(i).getTiles());
                if ((allHands.get(i).getTiles().get(j).getCountNumber() % 13)==(allHands.get(i).getTiles().get(j).getCountNumber())){
                    if((allHands.get(i).getTiles().get(j).getColor()==allHands.get(i).getTiles().get(j).getColor())){
                        sameColors.remove(allHands.get(i).getTiles().get(j));
                    }
                }
            }
        }

        return sameColors;
    }

    private ArrayList<Tile> allTilesArrayConstructor(){ // a private method for building an arraylist of all tiles with order.
        int colorCounter=0;             //colors as numbers:(YELLOW:1, BLUE:2, BLACK:3, RED:4, GREEN(FALSE JOKER):5)
        int secondPartCounter;          //a counter for the second occurences for each tile.
        for (int i =0; i<numberOfTiles; i++) {
            if (i < 54) {
                secondPartCounter=i;
                if (i % 13 == 0) {
                    colorCounter++;
                }
            } else {
                secondPartCounter=i-1;
                if ((i - 1) % 13 == 0) {
                    colorCounter++;
                }
            }
            if (colorCounter == 1) {
                Tile yellowTile = new Tile(Color.YELLOW, i, (secondPartCounter % 13) + 1);
                allTiles.add(yellowTile);
            }
            if (colorCounter == 2) {
                Tile blueTile = new Tile(Color.BLUE, i, (secondPartCounter % 13) + 1);
                allTiles.add(blueTile);
            }
            if (colorCounter == 3) {
                Tile blackTile = new Tile(Color.BLACK, i, (secondPartCounter % 13) + 1);
                allTiles.add(blackTile);
            }
            if (colorCounter == 4) {
                Tile redTile = new Tile(Color.RED, i, (secondPartCounter % 13) + 1);
                allTiles.add(redTile);
            }
            if (colorCounter == 5) {
                Tile falseJoker = new Tile(Color.GREEN, i, -1);
                allTiles.add(falseJoker);
                colorCounter = 1;
            }
        }
        return allTiles;
    }

    public ArrayList<Tile> getAllTiles() {
        return allTilesArrayConstructor();
    }
}
