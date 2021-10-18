import java.util.ArrayList;

public class Printer {
    ArrayList<Tile> allTiles = new ArrayList<>();
    ArrayList<Hand> allHands = new ArrayList<>();
    OkeyGame game = new OkeyGame(allTiles);

    public void tilesCreatorPrinter(){         //creating all the tiles

        allTiles= game.getAllTiles();
        System.out.println("ALL TILES WILL BE PRINTED.");
        System.out.println("--------------------------");

        for (Tile Tile : allTiles) {
            if(Tile.getColor()==Color.GREEN){
                System.out.println(Tile.getCountNumber()+" ------ "+Tile.getRealNumber()+" ------ False joker");
            }
            else {
                System.out.println(Tile.getCountNumber()+" ------ "+Tile.getRealNumber() + " ------ " + Tile.getColor());
            }
        }
        System.out.println("\n----------------------");
    }
    public void indicatorAndJokerCreatorPrinter(){     //setting indicator and joker before dealing tiles
        System.out.println("GAME IS STARTING.");
        System.out.println("----------------------");
        Tile indicator =game.chooseIndicator(allTiles);
        Tile joker = game.chooseJoker(allTiles,indicator);
        System.out.println("\nIndicator color:"+indicator.getColor()+" ------ Indicator number:"+indicator.getRealNumber());
        System.out.println("\nJoker color:"+joker.getColor()+" ------ Joker number:"+joker.getRealNumber());
        System.out.println("\n----------------------");
    }
    public void dealHandsPrinter(){// dealing tiles for the players

        allHands = game.dealTiles(allTiles);
        for(int i =0;i<4;i++){
            System.out.println("\nPlayer"+(i+1)+":"+allHands.get(i).getTiles());
        }
        System.out.println("\n----------------------");
    }

    public void bestHandPrinter(){
        System.out.println("Finding best hand algorithm is not yet implemented. :(");
        System.out.println("Some ideas are inserted with comment.");
    }

}
