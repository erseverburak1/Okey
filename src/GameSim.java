public class GameSim {
    public static void main(String[] args){
        Printer gamePrinter = new Printer();
        gamePrinter.tilesCreatorPrinter();
        gamePrinter.indicatorAndJokerCreatorPrinter();
        gamePrinter.dealHandsPrinter();
        gamePrinter.bestHandPrinter();
    }
}
